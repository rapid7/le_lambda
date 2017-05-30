# le_lambda
Follow the instructions below to send logs stored on AWS S3 to Logentries.

All source code and dependencies can be found on the [le_lambda Github page](https://github.com/logentries/le_lambda).

###### Example use cases:
* Forwarding AWS ELB and CloudFront logs
  * (make sure to set ELB/CloudFront to write logs every 5 minutes)
  * When forwarding these logs, the script will format the log lines according to Logentries KVP or JSON spec to make them easier to analyze
* Forwarding OpenDNS logs

## Obtain log token
1. Log in to your Logentries account

2. Add a new [token based log](https://logentries.com/doc/input-token/)

## Deploy the script to AWS Lambda using AWS CLI

1. Download the function source as zip from GitHub

2. Deploy the function:
   * Adjust the params as necessary, referring to [AWS docs](http://docs.aws.amazon.com/cli/latest/reference/lambda/create-function.html)

```
aws lambda create-function \
    --region us-east-1 \
    --function-name S3ToLE \
    --zip-file fileb://path/le_lambda.zip \
    --role role-arn \
    --environment Variables="{region=eu,token=token-uuid}" \
    --handler le_lambda.lambda_handler \
    --runtime python2.7 \
    --timeout 300 \
    --memory-size 512 \
    --profile default
```

3. Map the event source:
   * Adjust the params as necessary, referring to [AWS docs](http://docs.aws.amazon.com/lambda/latest/dg/with-cloudtrail-example-configure-event-source.html)

```
aws lambda add-permission \
--function-name CloudTrailEventProcessing \
--region us-west-2 \
--statement-id Id-1 \
--action "lambda:InvokeFunction" \
--principal s3.amazonaws.com \
--source-arn arn:aws:s3:::examplebucket \
--source-account examplebucket-owner-account-id \
--profile adminuser
```
   * Verify function's access policy:
```
aws lambda get-policy \
--function-name function-name \
--profile adminuser
```

   * Create event source mapping:

```
aws lambda create-event-source-mapping \
--function-name function-name \
--event-source-arn arn:aws:s3:::examplebucket
```


## Deploy the script to AWS Lambda using AWS Console
1. Create a new Lambda function

2. Choose the Python blueprint for S3 objects

   ![Choose Blueprint](https://raw.githubusercontent.com/logentries/le_lambda/master/doc/step2.png)

3. Configure triggers:
   * Choose the bucket log files are being stored in
   * Set event type "Object Created (All)"
   * Tick "Enable Trigger" checkbox

4. Configure function:
   * Give your function a name
   * Set runtime to Python 2.7

5. Upload function code:
   * Create a .ZIP file, containing ```le_lambda.py``` and the folder ```certifi```
     * Make sure the files and ```certifi``` folder are in the **root** of the ZIP archive
   * Choose "Upload a .ZIP file" in "Code entry type" dropdown and upload the archive created in previous step

6. Set Environment Variables:
   * Token value should match UUID provided by Logentries UI or API
   * Region should be that of your LE account - currently only ```eu```

   | Key       | Value      |
   |-----------|------------|
   | region    | eu         |
   | token     | token uuid |

7. Lambda function handler and role
   * Change the "Handler" value to ```le_lambda.lambda_handler```
   * Choose "Create a new role from template" from dropdown and give it a name below.
   * Leave "Policy templates" to pre-populated value

8. Advanced settings:
   * Set memory limit to a high enough value to facilitate log parsing and sending - adjust to your needs
   * Set timeout to a high enough value to facilitate log parsing and sending - adjust to your needs
   * Leave VPC value to "No VPC" as the script only needs S3 access
     * If you choose to use VPC, please consult [Amazon Documentation](http://docs.aws.amazon.com/lambda/latest/dg/vpc.html)

9. Enable function:
   * Click "Create function"

## Gotchas:
   * The "Test" button execution in AWS Lambda will **ALWAYS** fail as the trigger is not provided by the built in test function. In order to verify, upload a sample file to source bucket
