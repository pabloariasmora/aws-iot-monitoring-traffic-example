import boto3
client = boto3.client('iot')
response = client.describe_thing(
    thingName = 'iot-monitoring-example'
)

print(response)