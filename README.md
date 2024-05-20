# simple-minio-webhook

Simple webhook implementation that receives events from Minio (s3).

It reads the metadata file that describes REST API product and creates API and Product in the API Connect.


# set destination webhook
mc admin config set lh-s3 notify_webhook:service endpoint="http://mywebhookhost" queue_limit=0

mc admin service restart lh-s3

Notifications are per bucket



mc event add lh-s3/test-gas arn:minio:sqs::service:webhook --event put --suffix metadata_of_product.json