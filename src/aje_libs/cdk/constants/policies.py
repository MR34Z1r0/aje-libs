class PolicyUtils:
    """IAM policy statement utilities and predefined permissions"""
    
    @staticmethod
    def join_permissions(*permission_lists):
        """Combine multiple permission lists removing duplicates"""
        unique_permissions = set()
        for permissions in permission_lists:
            unique_permissions.update(permissions)
        return list(unique_permissions)
    
    # Predefined permission sets
    APPFLOW_READ_WRITE = [
        "appflow:TagResource",
        "appflow:DescribeFlow",
        "appflow:StartFlow",
        "appflow:StopFlow"
    ]
    
    S3_READ = [   
        "s3:ListBucket",
        "s3:GetObject",
        "s3:GetBucketLocation"
    ]
    
    S3_WRITE = [
        "s3:PutObject",
        "s3:DeleteObject"
    ]
    
    LOGS_PERMISSIONS = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
    ]
    