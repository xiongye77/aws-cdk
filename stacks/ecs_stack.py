from aws_cdk import core
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_autoscaling as autoscaling

class ECSStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str,vpc: ec2.Vpc, ** kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create ECS Cluster
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

        task_definition.add_container("DefaultContainer",
            image=ecs.ContainerImage.from_registry("amazon/amazon-ecs-sample"),
            memory_limit_mib = 512
        )

        # Instantiate an Amazon ECS Service
        ecs_service = ecs.Ec2Service(self, "Service",
            cluster=micro_service_cluster,
            task_definition=task_definition
        )
        
        lb =  core.Fn.import_value("ALB-name")
        lb_arn = core.Fn.import_value("ALB-ARN")
        listener_arn = core.Fn.import_value("ALB-Listener-ARN")
        #sg_id = core.Fn.import_value("ALB-SG")
        sg_id = "sg-0b8a86b7be5d58c84"
        existingAlb = elbv2.ApplicationLoadBalancer.from_application_load_balancer_attributes(self, "ImportedALB",load_balancer_arn=lb_arn,security_group_id=sg_id)
        existingListener = elbv2.ApplicationListener.from_application_listener_attributes(self, "ImportedListener",listener_arn=listener_arn,security_group_id=sg_id)
        #listener = existingAlb.add_listener("Listener", port=80)
        #existingListener.add_targets("ecs-service1",port=80,targets=[ecs_service])
        target_group_new = elbv2.ApplicationTargetGroup(self,"ecs-service1",vpc=vpc,port=80)
        target1 = existingListener.add_targets("ECS1",target_group_name= target_group_new.target_group_name,port=80,targets=[ecs_service])
      
