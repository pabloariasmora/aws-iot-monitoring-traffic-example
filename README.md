# Readme

1. Create an Iot Certificate.

```
aws iot create-keys-and-certificate --set-as-active --certificate-pem-outfile certs/certificate.pem.crt --private-key-outfile certs/private.pem.key
```

2. Grab the ARN as input for the next step
3. Step one deploy Cloudformation

```
aws cloudformation create-stack --stack-name iot-monitoring-example --template-body file://iot-monitoring.yaml --parameters ParameterKey=CertificateARN,ParameterValue=arn:aws:iot:us-east-1:ACCOUNTID:cert/1234 ParameterKey=EmailNotification,ParameterValue=valid@email.com
```

4. Confirm the email
5. Find the MQTT Endpoint using MQTT test client
6. Validate Connection

```
python pubsub.py --endpoint id-ats.iot.region.amazonaws.com --cert certs/certificate.pem.crt --key certs/private.pem.key --client_id iot-monitoring-example --topic test/topic --count 5
```

7. Force the throttle 

```
python pubsub.py --endpoint id-ats.iot.region.amazonaws.com --cert certs/certificate.pem.crt --key certs/private.pem.key --client_id iot-monitoring-example --topic test/topic --count 330
```
