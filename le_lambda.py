import boto3
import socket
import ssl
import datetime
import re
import csv
from le_config import *

print('Loading function')

s3 = boto3.client('s3')


def lambda_handler(event, context):
    host = 'data.logentries.com'
    port = 20000
    s_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s = ssl.wrap_socket(s_, ca_certs='le_certs.pem', cert_reqs=ssl.CERT_REQUIRED)
    s.connect((host, port))
    tokens = []
    if validate_uuid(debug_token) is True:
        tokens.append(debug_token)
    if validate_uuid(lambda_token) is True:
        tokens.append(lambda_token)
    else:
        pass

    if validate_uuid(log_token) is False:
        for token in tokens:
            s.sendall('%s %s\n' % (token, "{}: log token not present for username={}"
                                   .format(str(datetime.datetime.utcnow()), username)))
        raise SystemExit
    else:
        # Get the object from the event and show its content type
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            body = response['Body']
            data = body.read()
            for token in tokens:
                s.sendall('%s %s\n' % (token, "username='{}' downloaded file='{}' from bucket='{}'."
                                       .format(username, key, bucket)))
            lines = data.split("\n")
            for token in tokens:
                s.sendall('%s %s\n' % (token, "Beginning to send lines='{}' start_time='{}'."
                                       .format(str(len(lines)), str(datetime.datetime.utcnow()))))
            if validate_elb_log(str(key)) is True:
                # timestamp elb client:port backend:port request_processing_time backend_processing_time
                # response_processing_time elb_status_code backend_status_code received_bytes sent_bytes
                # "request" "user_agent" ssl_cipher ssl_protocol
                rows = csv.reader(data.splitlines(), delimiter=' ', quotechar='"')
                for line in rows:
                    request = line[11].split(' ')
                    idx = request[1].find('/', 9)
                    url = request[1][idx:]
                    parsed = {
                        'ip': line[2].split(':')[0],
                        'method': request[0],
                        'url': url,
                        'user_agent': line[12]
                    }
                    msg = "\"{0}\" ip=\"{ip}\" request_time=\"{5}\" elb_status=\"{7}\" backend_status=\"{8}\"" \
                          " bytes_received=\"{9}\" bytes_sent=\"{10}\" method=\"{method}\" url=\"{url}\"" \
                          " user_agent=\"{user_agent}\"\n"\
                        .format(*line, **parsed)
                    s.sendall(log_token + msg)
            else:
                for line in lines:
                    s.sendall('%s %s\n' % (log_token, line))
            for token in tokens:
                s.sendall('%s %s\n' % (token, "username='{}' finished sending log data end_time='{}'"
                                       .format(username, str(datetime.datetime.utcnow()))))
        except Exception as e:
            for token in tokens:
                print e
                s.sendall('%s %s\n' % (token, "Error getting username='{}' file='{}' from bucket='{}'. Make sure "
                                              "they exist and your bucket is in the same region as this function."
                                       .format(username, key, bucket)))
        finally:
            s.close()


def validate_uuid(uuid_string):
    regex = re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.I)
    match = regex.match(uuid_string)
    return bool(match)


def validate_elb_log(key):
    regex = re.compile('\d+_\w+_\w{2}-\w{4,9}-[12]_.*._\d{8}T\d{4}Z_\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}_.*.log$', re.I)
    match = regex.search(key)
    return bool(match)
