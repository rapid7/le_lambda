import boto3
import socket
import ssl
import datetime
import re
import csv
import json

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

# Used to send to debug log
username = "YOUR_USERNAME"

def lambda_handler(event, context):
    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    with LogentriesLogger(log_token, debug_token, lambda_token) as logger:
        parse_s3_object(bucket, key, logger)

def parse_s3_object(bucket, key, logger):
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        body = response['Body']

        data = body.read()

        msg = "username='{}' downloaded file='{}' from bucket='{}'.".format(username, key, bucket)
        logger.log_debug(msg)

        is_elb_data = validate_elb_log(str(key))
        parse_data(data, is_elb_data, logger)
    except Exception as e:
        print(e)
        msg = "Error getting username='{}' file='{}' from bucket='{}'. Make sure they exist and your bucket is in the same region as this function.".format(username, key, bucket)
        logger.log_debug(msg)

def parse_data(data, is_elb_data, logger):
    try:
        lines = data.split('\n')
        msg = "Beginning to send lines='{}' start_time='{}'.".format(str(len(lines)), str(datetime.datetime.utcnow()))
        logger.log_debug(msg)

        if is_elb_data is True:
            rows = csv.reader(data.splitlines(), delimiter=' ', quotechar='"')
            for line in rows:
                entry = customize_entry(line)
                logger.log_entry(entry)
        else:
            for line in lines:
                logger.log_entry(line)

        msg = "username='{}' finished sending log data end_time='{}'".format(username, str(datetime.datetime.utcnow()))
        logger.log_debug(msg)
    except Exception as e:
        print(e)
        logger.log_debug(e)

def customize_entry(line):
    # Get the log data in as a dictionary to easily work with it
    log = structure_elb_log(line)

    # To customize the log entry, modify the code below
    request = log['request'].split(' ')
    idx = request[1].find('/', 9)
    url = request[1][idx:]
    parsed = {
        'ip': log['client:port'].split(':')[0],
        'request_time': log['backend_processing_time'],
        'elb_status': log['elb_status_code'],
        'backend_status': log['backend_status_code'],
        'bytes_received': log['received_bytes'],
        'bytes_sent': log['sent_bytes'],
        'method': request[0],
        'url': url,
        'user_agent': log['user_agent']
    }

    # Log as key value pairs (a=b)
    format = ''.join(['%s="%s" ' % (k,v) for k,v in parsed.iteritems()])
    entry = '%s %s' % (log['timestamp'], format)

    # To log as JSON, set this variable to ture
    format_json = False
    if format_json is True:
        entry = json.dumps(parsed)

    return entry

def structure_elb_log(line):
    # Log value positions from http://docs.aws.amazon.com/ElasticLoadBalancing/latest/DeveloperGuide/access-log-collection.html#access-log-entry-format
    # timestamp elb client:port backend:port request_processing_time backend_processing_time
    # response_processing_time elb_status_code backend_status_code received_bytes sent_bytes
    # "request" "user_agent" ssl_cipher ssl_protocol

    parsed = {
        'timestamp': line[0],
        'elb': line[1],
        'client:port': line[2],
        'backend:port': line[3],
        'request_processing_time': line[4],
        'backend_processing_time': line[5],
        'response_processing_time': line[6],
        'elb_status_code': line[7],
        'backend_status_code': line[8],
        'received_bytes': line[9],
        'sent_bytes': line[10],
        'request': line[11],
        'user_agent': line[12],
        'ssl_cipher': line[13],
        'ssl_protocol': line[14]
    }
    return parsed

def validate_elb_log(key):
    # The split is done here to allow for input of an object
    # name that contains the full path in the bucket without
    # the bucket's name.
    key = key.split('/')[-1]
    regex = re.compile('^\d+_\w+_\w{2}-\w{4,9}-[12]_.*._\d{8}T\d{4}Z_\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}_.*.log$', re.I)
    match = regex.match(key)
    return bool(match)

class LogentriesLogger:
    def __init__(self, log_token, debug_token, lambda_token):
        host = 'data.logentries.com'
        port = 20000
        s_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s = ssl.wrap_socket(s_, ca_certs='le_certs.pem', cert_reqs=ssl.CERT_REQUIRED)
        s.connect((host, port))
        self.logentries_socket = s

        self.log_token = log_token
        self.lambda_token = lambda_token

        self.log_debug_tokens = []
        if self.validate_uuid(debug_token) is True:
            self.log_debug_tokens.append(debug_token)
        if self.validate_uuid(lambda_token) is True:
            self.log_debug_tokens.append(lambda_token)

        if self.validate_uuid(log_token) is False:
            self.log_debug("{}: log token not present for username={}"
                                   .format(str(datetime.datetime.utcnow()), username))
            raise SystemExit

    def log_entry(self, line):
        self.logentries_socket.sendall('%s %s\n' % (self.log_token, line))
        print(line)

    def log_debug(self, line):
        for token in self.log_debug_tokens:
            self.logentries_socket.sendall('%s %s\n' % (token, line))
        print(line)

    def validate_uuid(self, uuid_string):
        regex = re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.I)
        match = regex.match(uuid_string)
        return bool(match)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.logentries_socket.close();

class ConsoleLogger:
    def log_entry(self, line):
        print(line)

    def log_debug(self, line):
        print(line)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

if __name__ == "__main__":
    # To test, pick a logger

    # To setup a Logentries logger, uncomment the following line:
    # with LogentriesLogger(log_token, debug_token, lambda_token) as logger

    with ConsoleLogger() as logger:
        # You can test the output by calling a local ELB log file ...
        data = open('test-data.log').read().splitlines()

        # ... OR create a list of strings ...
        data = [
            '2015-05-13T23:39:43.945958Z my-loadbalancer 192.168.131.39:2817 10.0.0.1:80 0.000086 0.001048 0.001337 200 200 0 57 \"GET https://www.example.com:443/ HTTP/1.1\" \"curl/7.38.0\" DHE-RSA-AES128-SHA TLSv1.2',
            '2015-05-13T23:39:43.945958Z my-loadbalancer 192.168.131.39:2817 10.0.0.1:80 0.000086 0.001048 0.001337 200 200 0 57 \"GET https://www.example.com:443/ HTTP/1.1\" \"curl/7.38.0\" DHE-RSA-AES128-SHA TLSv1.2',
            '2015-05-13T23:39:43.945958Z my-loadbalancer 192.168.131.39:2817 10.0.0.1:80 0.000086 0.001048 0.001337 200 200 0 57 \"GET https://www.example.com:443/ HTTP/1.1\" \"curl/7.38.0\" DHE-RSA-AES128-SHA TLSv1.2',
            '2015-05-13T23:39:43.945958Z my-loadbalancer 192.168.131.39:2817 10.0.0.1:80 0.000086 0.001048 0.001337 200 200 0 57 \"GET https://www.example.com:443/ HTTP/1.1\" \"curl/7.38.0\" DHE-RSA-AES128-SHA TLSv1.2',
            '2015-05-13T23:39:43.945958Z my-loadbalancer 192.168.131.39:2817 10.0.0.1:80 0.000086 0.001048 0.001337 200 200 0 57 \"GET https://www.example.com:443/ HTTP/1.1\" \"curl/7.38.0\" DHE-RSA-AES128-SHA TLSv1.2',
            '2015-05-13T23:39:43.945958Z my-loadbalancer 192.168.131.39:2817 10.0.0.1:80 0.000086 0.001048 0.001337 200 200 0 57 \"GET https://www.example.com:443/ HTTP/1.1\" \"curl/7.38.0\" DHE-RSA-AES128-SHA TLSv1.2',
            '2015-05-13T23:39:43.945958Z my-loadbalancer 192.168.131.39:2817 10.0.0.1:80 0.000086 0.001048 0.001337 200 200 0 57 \"GET https://www.example.com:443/ HTTP/1.1\" \"curl/7.38.0\" DHE-RSA-AES128-SHA TLSv1.2'
        ]

        rows = csv.reader(data, delimiter=' ', quotechar='"')
        for line in rows:
            entry = customize_entry(line)
            logger.log_entry(entry)

        # ... OR can call an existing ELB log file in an S3 bucket
        # key = 'YOUR_LOG_FILE_NAME.log'
        # bucket = 'YOUR BUCKET NAME'
        # parse_s3_object(bucket, key, logger)
