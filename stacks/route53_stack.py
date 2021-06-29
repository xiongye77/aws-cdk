from aws_cdk import (
    aws_route53 as r53,
    aws_route53_targets as r53target,
    aws_iam as iam,
    aws_cloudfront as cdn,
    aws_ssm as ssm,
    core
) 

class DnsStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str,elbv2,  **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        prj_name = self.node.try_get_context("project_name")
        env_name = self.node.try_get_context("env")

        #hosted_zone = r53.HostedZone(self, 'hosted-zone',
        #    zone_name='aconex.design'
        #)

        hosted_zone = r53.HostedZone.from_hosted_zone_attributes(self,'hosted-zone',hosted_zone_id="Z2JDNY3K5WTR6X",zone_name="aconex.design")
        
        #r53.ARecord(self, 'cdn-record',
        #    zone=hosted_zone,
        #    target=r53.RecordTarget.from_alias(alias_target=r53target.CloudFrontTarget(cdnid)),
        #    record_name='app'
        #)

        r53.ARecord(self, "AliasRecord",
            zone=hosted_zone,
            target=r53.RecordTarget.from_alias(alias_target=r53target.LoadBalancerTarget(elbv2)),
            record_name='app'
        )

        ssm.StringParameter(self,'zone-id',
            parameter_name='/'+env_name+'/zone-id',
            string_value=hosted_zone.hosted_zone_id
        )
