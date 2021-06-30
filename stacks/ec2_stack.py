from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from aws_cdk import aws_autoscaling as autoscaling
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk import core


class EC2ServerStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, vpc: ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        prj_name = self.node.try_get_context("project_name")
        env_name = self.node.try_get_context("env")
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
        self.elbv2=alb
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
sudo mkdir /var/www/html/api
echo "<html><head><title>Modern Web App</title><style>body {margin-top: 40px;background-color: #333;}</style></head><body><div style=color:white;text-align:center><h1 style='font-size:7vw;'>Modern Web App</h1><p>Congratulations! Your Web Server is Online.</p><small>Pages served from $IP</small></div></body></html>" >> /var/www/html/api/index.html
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
                                                       min_capacity=1,
                                                       max_capacity=3,                                                      
                                                       user_data=ec2.UserData.custom(user_data)                                                           
                                                      )
        web_server_asg.scale_on_cpu_utilization("KeepCpuHalfwayLoaded",target_utilization_percent=50)
        

        # Allows ASG Security Group receive traffic from ALB
        web_server_asg.connections.allow_from(alb, ec2.Port.tcp(80),
                                              description="Allows ASG Security Group receive traffic from ALB")


        
        
        #listnerrule1 =elbv2.ApplicationListenerRule(    
        #    self, 
        #    id="listener rule1", 
        #    path_pattern="/", 
        #    priority=1, 
        #    listener=listener,
        #    target_groups=[web_server_asg]
        #)
        #target_group=listener.t
        #listnerrule1.add_target_group(target_group="aaaaa")

        micro_service_cluster = ecs.Cluster(
            self,
            "webServiceCluster",
            vpc=vpc        
        )
        
   
        # Define ECS Cluster Capacity
        micro_service_cluster.add_capacity(
            "microServiceAutoScalingGroup",
            instance_type=ec2.InstanceType("t2.micro")
        )

        # Deploy Container in the micro Service & Attach a LoadBalancer
        # Or add customized capacity. Be sure to start the Amazon ECS-optimized AMI.
        auto_scaling_group = autoscaling.AutoScalingGroup(self, "ASG",
            vpc=vpc,
            instance_type=ec2.InstanceType("t2.micro"),
            machine_image=ecs.EcsOptimizedImage.amazon_linux2(),
            # Or use Amazon ECS-Optimized Amazon Linux 2 AMI
            # machineImage: EcsOptimizedImage.amazonLinux2(),
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE),
            desired_capacity=1
        )

        micro_service_cluster.add_auto_scaling_group(auto_scaling_group)

        task_definition = ecs.Ec2TaskDefinition(self, "TaskDef")

        web_container = task_definition.add_container("DefaultContainer",
            image=ecs.ContainerImage.from_registry("dbaxy770928/carsales1:latest"),
            memory_limit_mib = 512                                
        )
        
        port_mapping = ecs.PortMapping(container_port=80)
        
        web_container.add_port_mappings(port_mapping)

        # Instantiate an Amazon ECS Service
        ecs_service = ecs.Ec2Service(self, "Service",
            cluster=micro_service_cluster,
            task_definition=task_definition
        )

                # Deploy Container in the micro Service with an Application Load Balancer
        
        #Fargate Task
        taskDefinition2 = ecs.FargateTaskDefinition(self, 'taskDef',
            memory_limit_mib = 512,
            cpu = 256,
        )

        web_container2=taskDefinition2.add_container('webContainer',
            image=ecs.ContainerImage.from_registry("dbaxy770928/carsales2:latest"),
        )
        
        port_mapping = ecs.PortMapping(container_port=80)
        
        web_container2.add_port_mappings(port_mapping)

        ecs_service2 = ecs.FargateService(self, "Service2",
            cluster=micro_service_cluster,
            task_definition=taskDefinition2,
            assign_public_ip= True
        )

        scalableTaget = ecs_service.auto_scale_task_count(max_capacity=5,min_capacity=1)
        scalableTaget.scale_on_memory_utilization("memory_usage",target_utilization_percent=75)
        scalableTaget.scale_on_cpu_utilization("cpu_usage",target_utilization_percent=70)
        #ecs_service.attach_to_application_target_group()
        # Add AutoScaling Group Instances to ALB Target Group
        #bbb =listener.add_targets("listenerId", port=80, targets=[web_server_asg])
        #aaa =listener.add_targets("ECS1", port=80, targets=[ecs_service])
        
        
        #ssm.StringListParameter.from_string_list_parameter_name(self,"acm_arn",string_list_parameter_name='/'+env_name+'/acm-arn')
        acm_arn=ssm.StringParameter.value_for_string_parameter(self,parameter_name='/'+env_name+'/acm-arn')
        
        listener.add_redirect_response("http-https",status_code="HTTP_301",port="443",protocol="HTTPS")
        HTTPSListener =alb.add_listener("https",port=443,certificate_arns=[acm_arn])
        
        aws_ec2 =HTTPSListener.add_targets("listenerId", port=80, targets=[web_server_asg])
        aws_ecs =HTTPSListener.add_targets("ECS1", port=80, targets=[ecs_service])
        aws_fargate =HTTPSListener.add_targets("ECS2", port=80, targets=[ecs_service2])

        elbv2.ApplicationListenerRule(self, 
            id="listener rule1", 
            path_pattern="/web/*", 
            priority=1, 
            listener=HTTPSListener,
            target_groups=[aws_ec2]
        )

        elbv2.ApplicationListenerRule(self, 
            id="listener rule2", 
            path_pattern="/api/*", 
            priority=2, 
            listener=HTTPSListener,
            target_groups=[aws_ecs]
        )

        elbv2.ApplicationListenerRule(self, 
            id="listener rule3", 
            path_pattern="/test/*", 
            priority=3, 
            listener=HTTPSListener,
            target_groups=[aws_fargate]
        )
        #elbv2.ApplicationListenerRule()
        # Add AutoScaling Group Instances to ALB Target Group
        # listener.add_targets("listenerId", port=80, targets=[web_server_asg])
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
                          
