#!/usr/bin/env python3

from aws_cdk import core
from stacks.vpc_stack import VPCStack
from stacks.ec2_stack import EC2ServerStack
from stacks.security_stack import SecurityStack
from stacks.bastion_stack import BastionStack
from stacks.kms_stack import KMSStack
from stacks.s3_stack import S3Stack
from stacks.rds_stack import RDSStack
from stacks.redis_stack import RedisStack
from stacks.cognito_stack import CognitoStack
from stacks.apigw_stack import APIStack
from stacks.lambda_stack import LambdaStack
from stacks.codepipeline_backend import CodePipelineBackendStack
from stacks.notifications import NotificationStack
from stacks.cdn_stack import CDNStack
from stacks.codepipeline_frontend import CodePipelineFrontendStack
from stacks.waf_stack import WafStack
from stacks.route53_stack import DnsStack
from stacks.acm_stack import ACMStack
from stacks.cloudtrail_stack import CloudTrailStack
from stacks.efs_stack import EFSStack
from stacks.kibana_stack import KibanaStack
#from stacks.ecs_stack import ECSStack

app = core.App()

vpc_stack = VPCStack(app, 'vpc')
security_stack = SecurityStack(app, 'security-stack', vpc=vpc_stack.vpc)

#ecs_stack = ECSStack(app,'ecs',vpc=vpc_stack.vpc)
bastion_stack = BastionStack(app, 'bastion', vpc=vpc_stack.vpc, sg=security_stack.bastion_sg)
kms_stack = KMSStack(app,'kms')
s3_stack = S3Stack(app,'s3buckets')
efs_stack = EFSStack(app, 'efs',vpc=vpc_stack.vpc)
rds_stack = RDSStack(app,'rds', vpc=vpc_stack.vpc, lambdasg=security_stack.lambda_sg, bastionsg=security_stack.bastion_sg, kmskey=kms_stack.kms_rds)
ec2server_stack = EC2ServerStack(app,'ec2',vpc=vpc_stack.vpc)
redis_stack = RedisStack(app,'redis', vpc=vpc_stack.vpc, redissg=core.Fn.import_value('redis-sg-export'))
cognito_stack = CognitoStack(app,'cognito')
apigw_stack = APIStack(app,'apigw')
lambda_stack = LambdaStack(app,'lambda')
cp_backend = CodePipelineBackendStack(app,'cp-backend', artifactbucket=core.Fn.import_value('build-artifacts-bucket') )
notification = NotificationStack(app,'notification')
cp_frontend = CodePipelineFrontendStack(app,'cp-frontend', webhostingbucket=core.Fn.import_value('frontend-bucket'))
waf_stack = WafStack(app,'waf')
acm_stack = ACMStack(app, 'acm')
cdn_stack = CDNStack(app,'cdn',s3bucket=core.Fn.import_value('frontend-bucket'),acmcert=acm_stack.cert_manager)
#route53 = DnsStack(app, 'route53',cdnid=cdn_stack.cdn_id)
route53 = DnsStack(app, 'route53',elbv2=ec2server_stack.elbv2)
cloudtrail = CloudTrailStack(app,'cloudtrail', s3bucket=s3_stack.cloudtrail_bucket)
kibana = KibanaStack(app,'kibana', vpc=vpc_stack.vpc, kibanasg=security_stack.kibana_sg)

app.synth()
