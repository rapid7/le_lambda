import boto3
import socket
import ssl
import datetime
import re
import urllib
import csv
import zlib
import json
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
        key = urllib.unquote_plus(event['Records'][0]['s3']['object']['key']).decode('utf8')
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            body = response['Body']
            data = body.read()
            # If the name has a .gz extension, then decompress the data
            if key[-3:] == '.gz':
                data = zlib.decompress(data, 16+zlib.MAX_WBITS)
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
            elif validate_cf_log(str(key)) is True:
                # date time x-edge-location sc-bytes c-ip cs-method cs(Host)
                # cs-uri-stem sc-status cs(Referer) cs(User-Agent) cs-uri-query
                # cs(Cookie) x-edge-result-type x-edge-request-id x-host-header
                # cs-protocol cs-bytes time-taken x-forwarded-for ssl-protocol
                # ssl-cipher x-edge-response-result-type
                rows = csv.reader(data.splitlines(), delimiter='\t', quotechar='"')
                for line in rows:
                    # Skip headers and lines with insufficient values
                    if len(line) != 23:
                        continue
                    msg = "\"{0}T{1}Z\" x_edge_location=\"{2}\"" \
                          " sc_bytes=\"{3}\" c_ip=\"{4}\" cs_method=\"{5}\"" \
                          " cs_host=\"{6}\" cs_uri_stem=\"{7}\" sc_status=\"{8}\"" \
                          " cs_referer=\"{9}\" cs_user_agent=\"{10}\" cs_uri_query=\"{11}\"" \
                          " cs_cookie=\"{12}\" x_edge_result_type=\"{13}\"" \
                          " x_edge_request_id=\"{14}\" x_host_header=\"{15}\"" \
                          " cs_protocol=\"{16}\" cs_bytes=\"{17}\" time_taken=\"{18}\"" \
                          " x_forwarded_for=\"{19}\" ssl_protocol=\"{20}\"" \
                          " ssl_cipher=\"{21}\" x_edge_response_result_type=\"{22}\"\n" \
                        .format(*line)
                    s.sendall(log_token + msg)
            elif validate_ct_log(str(key)) is True:
                cloud_trail = json.loads(data)
                for event in cloud_trail['Records']:
                    s.sendall('%s %s\n' % (log_token, json.dumps(event)))
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


def validate_cf_log(key):
    regex = re.compile('\w+\.\d{4}-\d{2}-\d{2}-\d{2}\.\w+\.gz$', re.I)
    match = regex.search(key)
    return bool(match)


def validate_ct_log(key):
    regex = re.compile('\d+_CloudTrail_\w{2}-\w{4,9}-[12]_\d{8}T\d{4}Z.+.json.gz$', re.I)
    match = regex.search(key)
    return bool(match)
