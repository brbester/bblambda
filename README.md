## bblambda

An example implementation of a Cisco Spark bot in AWS Lambda using APIGateway on the front end, and DynamoDB on the back...

### Installation

Installation is straighforward, copy the code into a new AWS Lambda with permissions set properly.  Setup API Gateway to receive a webhook from Cisco Spark and pass the event via a proxy to Lambda.  Create a DynamoDB table.  Fill in all the global variables in lambda for these bits of info and your various API keys (and Cisco Spark Webhook secret).  Create the bot at developer.ciscospark.com and then the webhook pointing to the APIGateway address.
