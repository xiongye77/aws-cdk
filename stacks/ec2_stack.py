from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_autoscaling as autoscaling
from aws_cdk import core


class EC2ServerStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, vpc: ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Read BootStrap Script):
        try:
            with open("bootstrap_scripts/install_httpd.sh11", mode="r") as file:
                user_data = file.read()
        except OSError:
            print('Unable to read UserData script')

        linux_ami = ec2.AmazonLinuxImage(generation= ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
                                          edition=ec2.AmazonLinuxEdition.STANDARD,
                                          virtualization=ec2.AmazonLinuxVirt.HVM,
                                          storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE
                                          )

        # Create Application Load Balancer
        alb = elbv2.ApplicationLoadBalancer(
            self,
            "myAlbId",
            vpc=vpc,
            internet_facing=True,
            load_balancer_name="WebServerAlb"
        )

        # Allow ALB to receive internet traffic
        alb.connections.allow_from_any_ipv4(
            ec2.Port.tcp(80),
            description="Allow Internet access on ALB Port 80"
        )

        # Add Listerner to ALB
        listener = alb.add_listener("listernerId",
                                    port=80,
                                    open=True)

        # Webserver IAM Role
        web_server_role = iam.Role(self, "webServerRoleId",
                                    assumed_by=iam.ServicePrincipal(
                                        'ec2.amazonaws.com'),
                                    managed_policies=[
                                        iam.ManagedPolicy.from_aws_managed_policy_name(
                                            'AmazonSSMManagedInstanceCore'
                                        ),
                                        iam.ManagedPolicy.from_aws_managed_policy_name(
                                            'AmazonS3ReadOnlyAccess'
                                        )
                                    ])
        user_data = """
#!/bin/bash -xe

# Lets log everything to console for being lazy (not recommended)
# exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

sudo yum install -y httpd
IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
echo "<html><head><title>Modern Web App</title><style>body {margin-top: 40px;background-color: #333;}</style></head><body><div style=color:white;text-align:center><h1 style='font-size:7vw;'>Modern Web App</h1><p>Congratulations! Your Web Server is Online.</p><small>Pages served from $IP</small></div></body></html>" >> /var/www/html/index.html
sudo chkconfig httpd on
sudo service httpd start
"""
        web_server_asg = autoscaling.AutoScalingGroup(self,
                                                       "webServerAsgId",
                                                       vpc=vpc,
                                                       vpc_subnets= ec2.SubnetSelection(
                                                           subnet_type=ec2.SubnetType.PRIVATE
                                                       ),
                                                       instance_type=ec2.InstanceType(
                                                           instance_type_identifier="t2.micro"),
                                                       machine_image=linux_ami,
                                                       role=web_server_role,
                                                       min_capacity=2,
                                                       max_capacity=2,                                                      
                                                       user_data=ec2.UserData.custom(user_data)                                                           
                                                      )

        # Allows ASG Security Group receive traffic from ALB
        web_server_asg.connections.allow_from(alb, ec2.Port.tcp(80),
                                              description="Allows ASG Security Group receive traffic from ALB")

        # Add AutoScaling Group Instances to ALB Target Group
        listener.add_targets("listenerId", port=80, targets=[web_server_asg])

        # Output of the ALB Domain Name
        output_alb_1 = core.CfnOutput(self,
                                      "albDomainName",
                                      value=f"http://{alb.load_balancer_dns_name}",
                                      description="Web Server ALB Domain Name")
        output_alb_2 = core.CfnOutput(self,
                                      "ALB-name",
                                      value=alb.load_balancer_dns_name,
                                      description="Web Server ALB Domain Name",
                                      export_name="ALB-name")
        output_alb_arn = core.CfnOutput(self,
                                      "ALB-ARN",
                                      value=alb.load_balancer_arn,
                                      description="Web Server ALB ARN",
                                      export_name="ALB-ARN")
        output_listener_arn = core.CfnOutput(self,
                                      "ALB-Listener-ARN",
                                      value=listener.listener_arn,
                                      description="ALB-Listener-ARN",
                                      export_name="ALB-Listener-ARN")                              
