# le_lambda
Follow the instructions below to send logs stored on AWS S3 to Logentries.

All source code can be found on the [le_lambda Github page](https://github.com/logentries/le_lambda).

###### Example use cases:
* Forwarding AWS ELB and CloudFront logs
  * (make sure to set ELB/CloudFront to write logs every 5 minutes)
  * When forwarding these logs, the script will format the log lines according to Logentries KVP spec to make them easier to analyze
* Forwarding OpenDNS logs

## Obtain log token(s)
1. Log in to your Logentries account

2. Add a new [token based log](https://logentries.com/doc/input-token/)
   * Optional: repeat to add second log for debugging

## Deploy the script on AWS Lambda
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

5. Edit code:
   * Edit the contents of ```le_config.py```
   * Replace values of ```log_token``` and ```debug_token``` with tokens obtained earlier.
   * Create a .ZIP file, containing the updated ```le_config.py```, ```le_lambda.py``` and ```le_certs.pem```
     * Make sure the files are in the root of the ZIP archive, and **NOT** in a folder
   * Choose "Upload a .ZIP file" in "Code entry type" dropdown and upload the archive created in previous step

6. Lambda function handler and role
   * Change the "Handler" value to ```le_lambda.lambda_handler```
   * Choose "Create a new role from template" from dropdown and give it a name below.
   * Leave "Policy templates" to pre-populated value

7. Advanced settings:
   * Set memory to 1536 MB (script only runs for seconds at a time)
   * Set timeout to a high value, just below of log file creation frequency
     *  Below example is configured for ELB logs written every 5 minutes
   * Leave VPC value to "No VPC" as the script only needs S3 access
     * If you choose to use VPC, please consult [Amazon Documentation](http://docs.aws.amazon.com/lambda/latest/dg/vpc.html)

8. Enable function:
   * Click "Create function"

## Gotchas:
   * The "Test" button execution in AWS Lambda will **ALWAYS** fail as the trigger is not provided by the built in test function. In order to verify, upload a sample file to source bucket
