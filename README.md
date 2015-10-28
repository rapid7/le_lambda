# le_lambda
Follow the instructions below to send logs stored on AWS S3 to Logentries.

###### Example use cases:
* Forwarding AWS ELB logs
  * (make sure to set ELB to write logs every 5 minutes)
* Forwarding OpenDNS logs

## Obtain log token(s)
1. Log in to your Logentries account
2. Add a new [token based log](https://logentries.com/doc/input-token/)
   * Optional: repeat to add second log for debugging

## Deploy the script on AWS Lambda
1. Create a new Lambda function

   ![Create Function](https://raw.githubusercontent.com/omgapuppy/le_lambda/master/doc/step1.png)

2. Choose the Python blueprint for S3 objects

   ![Choose Blueprint](https://raw.githubusercontent.com/omgapuppy/le_lambda/master/doc/step2.png)

3. Configure event sources:
   * Select S3 as event source type
   * Choose the bucket log files are being stored in
   * Set event type "Object Created (All)"

   ![Create Function](https://raw.githubusercontent.com/omgapuppy/le_lambda/master/doc/step3.png)

4. Configure function:
   * Give your function a name
   * Set runtime to Python 2.7

   ![Create Function](https://raw.githubusercontent.com/omgapuppy/le_lambda/master/doc/step4.png)

5. Edit code:
   * Select "Edit code inline"
   * Copy the contents of ```le_lambda.py```
   * Replace **all** code in the editor window
   * Replace values of ```log_token``` and ```debug_token``` with tokens obtained earlier.

   ![Create Function](https://raw.githubusercontent.com/omgapuppy/le_lambda/master/doc/step5.png)

6. Lambda function handler and role
   * Leave the "Handler" value to default
   * Create a new S3 execution role (your IAM user must have sufficient permissions to create & assign new roles)

   ![Create Function](https://raw.githubusercontent.com/omgapuppy/le_lambda/master/doc/step6.png)

7. Allocate resources:
   * Set memory to 1536 MB (script only runs for seconds at a time)
   * Set timeout to a high value, just below of log file creation frequency
     *  Below example is configured for ELB logs written every 5 minutes

  ![Create Function](https://raw.githubusercontent.com/omgapuppy/le_lambda/master/doc/step7.png)

8. Enable function:
   * Select "Enable now"
   * Click "Create function"

   ![Create Function](https://raw.githubusercontent.com/omgapuppy/le_lambda/master/doc/step8.png)
   
   ![Create Function](https://raw.githubusercontent.com/omgapuppy/le_lambda/master/doc/step9.png)
