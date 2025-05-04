from aws_cdk import (
    Tags, Duration, SecretValue,
    aws_iam as iam,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
    aws_glue as glue,
    aws_dynamodb as dynamodb,
    aws_dms as dms,
    aws_lambda as _lambda,
    aws_stepfunctions as sf,
    aws_sns as sns,
    aws_apigateway as apigw,
    aws_sqs as sqs
)
from ..constants.services import Services
from ..constants.policies import PolicyUtils
from ..constants.environments import Environments
from ..constants.project_config import ProjectConfig
from ..models.configs import *
from .name_builder import NameBuilder

class ResourceBuilder:
    """Main builder class for AWS CDK resources"""
    
    def __init__(self, stack, project_config: ProjectConfig):
        self.stack = stack 
        self.project_config = project_config 
        self.name_builder = NameBuilder(self.project_config)
        
    # Lambda Resources
    def build_lambda_function(self, config: LambdaConfig) -> _lambda.Function:
        """Create a Lambda function with standardized configuration"""
        function_name = self.name_builder.build(Services.LAMBDA_FUNCTION, config.function_name)        
        fn = _lambda.Function(  
            self.stack, function_name,
            function_name=function_name,
            runtime=config.runtime,
            handler=config.handler,
            code=_lambda.Code.from_asset(config.code_path),
            memory_size=config.memory_size,
            environment=config.environment,
            layers=config.layers,
            timeout=config.timeout,
            role=config.role
        )        
        self.tag_resource(fn, function_name, "AWS Lambda")        
        return fn
        
    # DynamoDB Resources
    def build_dynamodb_table(self, config: DynamoDBConfig) -> dynamodb.Table:
        """Create a DynamoDB table with standard configuration"""
        table_name = self.name_builder.build(Services.DYNAMODB_TABLE, config.table_name)
        
        table = dynamodb.Table(
            self.stack, table_name,
            table_name=table_name,
            partition_key=dynamodb.Attribute(
                name=config.partition_key,
                type=config.partition_key_type
            ),
            sort_key=dynamodb.Attribute(
                name=config.sort_key,
                type=config.sort_key_type
            ) if config.sort_key else None,
            stream=config.stream,
            billing_mode=config.billing_mode,
            removal_policy=config.removal_policy,
            encryption=config.encryption,
            point_in_time_recovery=config.point_in_time_recovery  
        )
        
        self.tag_resource(table, table_name, "AWS DynamoDB")
        return table
            
    def tag_resource(self, resource, name: str, service_name: str):
        """Apply standard tagging to resources"""
        Tags.of(resource).add("Enterprise", self.project_config.enterprise)
        Tags.of(resource).add("Project", self.project_config.project_name)
        Tags.of(resource).add("Environment", self.project_config.environment.value)
        Tags.of(resource).add("Name", name)
        Tags.of(resource).add("Service", service_name)
        Tags.of(resource).add("Owner", self.project_config.author)
    
    def import_secret(self, secret_name: str) -> secretsmanager.Secret:
        """Import an existing secret"""
        return secretsmanager.Secret.from_secret_name_v2(
            self.stack, secret_name, secret_name
        )
        
    def import_dynamodb_table(self, table_name: str) -> dynamodb.Table:
        """Import an existing DynamoDB table"""
        return dynamodb.Table.from_table_name(
            self.stack, table_name, table_name
        )

    def build_lambda_rest_api(self, config: LambdaRestApiConfig) -> apigw.LambdaRestApi:
        """Create a Lambda function with standardized configuration"""
        rest_api_name = self.name_builder.build(Services.API_GATEWAY, config.rest_api_name)
        
        api = apigw.LambdaRestApi(  
            self.stack, rest_api_name,
            rest_api_name=rest_api_name, 
            description=config.description,
            handler=config.handler,
            deploy_options=config.deploy_options,
            default_cors_preflight_options=config.default_cors_preflight_options,
            default_method_options=config.default_method_options,
            endpoint_types=config.endpoint_types,
            cloud_watch_role=config.cloud_watch_role,
            proxy=config.proxy,
        )
        
        self.tag_resource(api, rest_api_name, "AWS API Gateway")        
        return api

    def build_sqs_queue(self, config: SQSConfig) -> sqs.Queue:
        """Create a new SQS queue with standard configuration"""
        queue_name = self.name_builder.build(Services.SQS, config.queue_name)
        queue = sqs.Queue(
            self.stack, queue_name,
            queue_name=queue_name,
            visibility_timeout=config.visibility_timeout,
            retention_period=config.retention_period,
            fifo=config.fifo,
            content_based_deduplication=config.content_based_deduplication,
            removal_policy=config.removal_policy
        )
        self.tag_resource(queue, queue_name, "AWS SQS")
        return queue

    ##################################################################
    # Secrets Manager Resources
    def build_secret(self, secret_name: str, secret_value: str) -> secretsmanager.Secret:
        """Create a new secret with standard configuration"""
        secret_name = self.name_builder.build(Services.SECRET, secret_name)
        secret = secretsmanager.Secret(
            self.stack, secret_name,
            secret_name=secret_name,
            secret_string_value=SecretValue.unsafe_plain_text(secret_value)
        )
        self.tag_resource(secret, secret_name, "AWS Secrets Manager")
        return secret
    # S3 Resources
    def build_s3_bucket(self, config: S3Config) -> s3.Bucket:
        """Create a new S3 bucket with standard configuration"""
        bucket_name = self.name_builder.build(Services.S3_BUCKET, config.bucket_name)
        bucket = s3.Bucket(
            self.stack, bucket_name,
            bucket_name=bucket_name,
            block_public_access=config.block_public_access,
            versioned=config.versioned,
            removal_policy=config.removal_policy
        )
        self.tag_resource(bucket, bucket_name, "AWS S3")
        return bucket
    
    def import_s3_bucket(self, config: S3Config) -> s3.Bucket:
        """Import an existing S3 bucket"""
        bucket_name = self.name_builder.build(Services.S3_BUCKET, config.bucket_name)
        return s3.Bucket.from_bucket_name(
            self.stack, bucket_name, bucket_name
        )
    
    def import_api_gateway(self, config: ApiGatewayConfig) -> apigw.RestApi:
        """Import an existing API Gateway"""
        api_name = self.name_builder.build(Services.API_GATEWAY, config.name)
        return apigw.RestApi.from_rest_api_id(
            self.stack, api_name, api_name
        )

    # API Gateway Resources    
    def build_api_gateway(self, config: ApiGatewayConfig) -> apigw.RestApi:
        """Create a new API Gateway with standard configuration"""
        api_name = self.name_builder.build(Services.API_GATEWAY, config.name)
        
        api = apigw.RestApi(
            self.stack, api_name,
            rest_api_name=api_name,
            description=config.description,
            endpoint_types=config.endpoint_types,
            deploy=config.deploy,
            policy=config.policy,
            binary_media_types=config.binary_media_types,
            minimum_compression_size=config.minimum_compression_size,
        )
        
        self.tag_resource(api, api_name, "AWS API Gateway")
        return api
     
    def build_api_gateway_deployment(self, config: ApiGatewayDeploymentConfig) -> apigw.Deployment:
        """Create a new API Gateway deployment with standard configuration"""         
        deployment = apigw.Deployment(
            self.stack, config.deployment_name,
            api=config.api,
            description=config.description
        )        
        self.tag_resource(deployment, config.deployment_name, "AWS API Gateway")
        return deployment

    def build_api_gateway_stage(self, config: ApiGatewayStageConfig) -> apigw.Stage:
        """Create a new API Gateway stage with standard configuration"""
         
        stage = apigw.Stage(
            self.stack, config.stage_name,
            deployment=config.deployment,
            stage_name=config.stage_name,
            data_trace_enabled=config.data_trace_enabled,
            logging_level=config.logging_level
        )        
        self.tag_resource(stage, config.stage_name, "AWS API Gateway")
        return stage

    # Glue Resources
    def build_glue_job(self, config: GlueJobConfig) -> glue.CfnJob:
        """Create a Glue ETL job with standard configuration"""
        glue_job_name = self.name_builder.build(Services.GLUE_JOB, config.name)
        
        job = glue.CfnJob(
            self.stack, glue_job_name,
            name=glue_job_name,
            command=glue.CfnJob.JobCommandProperty(
                name="glueetl",
                python_version="3",
                script_location=f"s3://{config.artifacts_bucket.bucket_name}/{config.script_path}"
            ),
            default_arguments=config.environment,
            glue_version=config.glue_version,
            worker_type=config.worker_type,
            number_of_workers=config.worker_count,
            role=config.role.role_arn
        )
        
        self.tag_resource(job, glue_job_name, "AWS Glue")
        return job
    
    def import_glue_job(self, config: GlueJobConfig) -> glue.CfnJob:
        """Import an existing Glue job"""
        glue_job_name = self.name_builder.build(Services.GLUE_JOB, config.name)
        
        job = glue.CfnJob.from_job_name(
            self.stack, glue_job_name, glue_job_name
        )
    
    # DMS Resources
    def build_dms_endpoint(self, config: DMSEndpointConfig) -> dms.CfnEndpoint:
        """Create a DMS endpoint with standard configuration"""
        endpoint_name = self.name_builder.build(Services.DMS_ENDPOINT, config.name)
        
        endpoint = dms.CfnEndpoint(
            self.stack, endpoint_name,
            endpoint_name=endpoint_name,
            engine_name=config.engine_name,
            username=config.username,
            password=config.password,
            server_name=config.server_name,
            port=config.port,
            database_name=config.database_name,
            s3_settings=config.s3_settings,
            kms_settings=config.kms_settings,
            tags=config.tags
        )
        
        self.tag_resource(endpoint, endpoint_name, "AWS DMS")
        return endpoint
    
    # Step Functions Resources
    def build_step_function(self, config: StepFunctionConfig) -> sf.StateMachine:
        """Create a Step Functions state machine with standard configuration"""
        state_machine_name = self.name_builder.build(Services.STEP_FUNCTION, config.name)
        
        state_machine = sf.StateMachine(
            self.stack, state_machine_name,
            state_machine_name=state_machine_name,
            definition=config.definition,
            timeout=Duration.minutes(config.timeout)
        )
        
        self.tag_resource(state_machine, state_machine_name, "AWS Step Functions")
        return state_machine
    
    # SNS Resources
    def build_sns_topic(self, config: SNSTopicConfig) -> sns.Topic:
        """Create a SNS topic with standard configuration"""
        topic_name = self.name_builder.build(Services.SNS_TOPIC, config.name)
        
        topic = sns.Topic(
            self.stack, topic_name,
            topic_name=topic_name,
            display_name=config.display_name,
            master_key=config.master_key, 
            delivery_policy=config.delivery_policy,
            subscriptions=config.subscriptions,
            tags=config.tags
        )
        
        self.tag_resource(topic, topic_name, "AWS SNS")
        return topic
    
    def import_sns_topic(self, topic_name: str) -> sns.Topic:
        """Import an existing SNS topic"""
        internal_name = self.name_builder.build(Services.SNS_TOPIC, topic_name)
        return sns.Topic.from_topic_arn(
            self.stack, internal_name, f"arn:aws:sns:{self.stack.region}:{self.stack.account}:{topic_name}"
        )   