from enum import Enum

class Services(Enum):
    """AWS Service identifiers for resource naming and tagging"""
    S3_BUCKET = 's3'
    LAMBDA_FUNCTION = 'fn'
    STEP_FUNCTION = 'sf'
    IAM_ROLE = 'role'
    IAM_POLICY = 'policy'
    GLUE_JOB = 'job'
    GLUE_CONNECTION = 'cnx'
    GLUE_CRAWLER = 'cw'
    GLUE_DATABASE = 'db'
    SNS_TOPIC = 'sns'
    DMS_TASK = 'dms'
    DMS_INSTANCE = 'dmsi'
    DMS_ENDPOINT = 'dmse'
    DYNAMODB_TABLE = 'ddb'
    SECRET = 'sm'
    EVENT_BRIDGE = 'eb'
    API_GATEWAY = 'api'
    SQS = 'sqs'

class DMSEndpointType(Enum):
    """DMS Endpoint type identifiers"""
    SOURCE = 1
    TARGET = 2