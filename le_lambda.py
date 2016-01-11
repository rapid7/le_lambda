import boto3
import socket
import datetime
import re
import csv
print('Loading function')

s3 = boto3.client('s3')

# This token is used to associate log files in AWS S3 to a log in your Logentries account.
log_token = "YOUR_LOG_TOKEN"

# You can supply an optional token to log activity to a log on Logentries and any errors from this script.
# This is optional, it is recommended you use one log file/token for all your Lambda scripts. If you do not
# wish to use this, just leave the value blank.
debug_token = "YOUR_DEBUG_TOKEN"

# Log to generic activity from this script to our support logging system for Lambda scripts
# this is optional, but helps us improve our service nad can be hand for us helping you debug any issues
# just remove this token if you wish (leave variable in place)
lambda_token = "0ae0162e-855a-4b54-9ae3-bd103006bfc0"

username = "YOUR_USERNAME"


def lambda_handler(event, context):
    host = 'data.logentries.com'
    port = 80
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    tokens = []
    if validate_uuid4(debug_token) is True:
        tokens.append(debug_token)
    if validate_uuid4(lambda_token) is True:
        tokens.append(lambda_token)
    else:
        pass

    if validate_uuid4(log_token) is False:
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
                s.sendall('%s %s\n' % (token, "username={} downloaded file={} from bucket={}."
                                       .format(username, key, bucket)))
            lines = data.split("\n")
            for token in tokens:
                s.sendall('%s %s\n' % (token, "Beginning to send lines={} start_time={}."
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
                s.sendall('%s %s\n' % (token, "username={} finished sending log data end_time={}"
                                       .format(username, str(datetime.datetime.utcnow()))))
        except Exception as e:
            for token in tokens:
                print e
                s.sendall('%s %s\n' % (token, 'Error getting username={} file={} from bucket={}. Make sure '
                                              'they exist and your bucket is in the same region as this function.'
                                       .format(username, key, bucket)))
        finally:
            s.close()


def validate_uuid4(uuid):
    regex = re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.I)
    match = regex.match(uuid)
    return bool(match)


def validate_elb_log(key):
    regex = re.compile('^\d+_\w+_\w{2}-\w{4,9}-[12]_.*._\d{8}T\d{4}Z_\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}_.*.log$', re.I)
    match = regex.match(key)
    return bool(match)
