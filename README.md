# le_lambda
Follow the instructions below to send logs stored on AWS S3 to Logentries.

###### Example use cases:
* Forwarding AWS ELB logs
  * (make sure to set ELB to write logs every 5 minutes)
  * When forwarding ELB logs, the script will format the log lines according to Logentries KVP spec to make them easier to analyze
* Forwarding OpenDNS logs

## Obtain log token(s)
1. Log in to your Logentries account
2. Add a new [token based log](https://logentries.com/doc/input-token/)
   * Optional: repeat to add second log for debugging

## Deploy the script on AWS Lambda
1. Create a new Lambda function

   ![Create Function](https://raw.githubusercontent.com/logentries/le_lambda/master/doc/step1.png)

2. Choose the Python blueprint for S3 objects

   ![Choose Blueprint](https://raw.githubusercontent.com/logentries/le_lambda/master/doc/step2.png)

3. Configure event sources:
   * Select S3 as event source type
   * Choose the bucket log files are being stored in
   * Set event type "Object Created (All)"

   ![Create Function](https://raw.githubusercontent.com/logentries/le_lambda/master/doc/step3.png)

4. Configure function:
   * Give your function a name
   * Set runtime to Python 2.7

   ![Create Function](https://raw.githubusercontent.com/logentries/le_lambda/master/doc/step4.png)

5. Edit code:
   * Edit the contents of ```le_config.py```
   * Replace values of ```log_token``` and ```debug_token``` with tokens obtained earlier.
   * Create a .ZIP file, containing the updated ```le_config.py```, ```le_lambda.py``` and ```le_certs.pem```
   * Choose "Upload a .ZIP file" in AWS Lambda and upload the archive created in previous step

   ![Create Function](https://raw.githubusercontent.com/logentries/le_lambda/master/doc/step5.png)

6. Lambda function handler and role
   * Change the "Handler" value to ```le_lambda.lambda_handler```
   * Create a new S3 execution role (your IAM user must have sufficient permissions to create & assign new roles)

   ![Create Function](https://raw.githubusercontent.com/logentries/le_lambda/master/doc/step6.png)

7. Allocate resources:
   * Set memory to 1536 MB (script only runs for seconds at a time)
   * Set timeout to a high value, just below of log file creation frequency
     *  Below example is configured for ELB logs written every 5 minutes

  ![Create Function](https://raw.githubusercontent.com/logentries/le_lambda/master/doc/step7.png)

8. Enable function:
   * Select "Enable now"
   * Click "Create function"

   ![Create Function](https://raw.githubusercontent.com/logentries/le_lambda/master/doc/step8.png)

   ![Create Function](https://raw.githubusercontent.com/logentries/le_lambda/master/doc/step9.png)
