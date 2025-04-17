# cuOpt on NVCF

## Model Overview

### Description

**NVIDIA cuOpt** is an AI microservice that optimizes logistics routing to save enterprises money, increase revenue, and reduce carbon emissions. It offers dynamic rerouting, horizontal load-balancing, and robotic simulations, with sub second solver response times. cuOpt enables organizations to easily access world record accelerated optimization capabilities across multi- and hybrid cloud environments. It solves complex routing problems with multiple constraints and delivers new capabilities, empowering teams to make dynamic, data-driven decisions.

Today, cuOpt focuses primarily on variants of Vehicle Routing Problems (VRP) such as Capacitated Vehicle Routing Problems (CVRP), Capacitated Vehicle Routing with Time Windows (CVRTW), and Pick up and Delivery with Time Windows (PDPTW). To solve these problems, NVIDIA cuOpt uses GPU-accelerated logistics solvers relying on heuristics, metaheuristics, and optimization to calculate complex vehicle-routing-problem variants with a wide range of constraints.Typical Use Cases

1. **Last Mile Delivery (LMD)**: A fleet of vehicles is tasked with serving customers at multiple locations or demand points, typically with the goal of minimizing total costs, such as fleet size, distance traveled or time taken, while satisfying various constraints and objectives. Each customer has specific demand along with other constraints such as time windows and other service level agreements. Each vehicle may be bound by constraints such as such as maximum load capacity, maximum travel distance, emission types and availability. In Manufacturing, the last mile is the supply of components in a production process, e.g., the delivery of parts to the plant. In Distribution (B2B), the last mile is the supply of stock to physical stores for in-store experiences. In E-Commerce (B2C)/Grocery/Parcel/Quick Service delivery, the last mile is the hand-off point to customer or to a prearranged drop-off location.

1. **Dispatch Optimization**: This involves the allocation and scheduling of field service technicians to fulfill customer orders, service requests or deliveries. Determining the most efficient routes for vehicles or technicians based on factors such as location, capacity, availability, skillset, priority, and regulatory compliance. The objective could be to minimize travel time, distance, fuel consumption, maximize the number of tasks or service calls, or minimize empty space and unnecessary trips. Implement continuous optimization by processing dynamic events to accommodate changes, disruptions, or new requests while increasing productivity and maintaining service level agreements (SLAs). Option available to allocate tasks evenly by balancing workload distribution to prevent overloading or under-utilization of service personnel. Dispatch optimization is essential for any businesses with field service operations, transportation and logistics, emergency response teams, health or hunger drives and any other operations that involve routing of field assets.

1. **Pickup and Delivery (PDP)**: This involves determining the most efficient routes for a fleet of vehicles to pick up items from specified pick-up points and deliver them to specified drop-off points, while satisfying various constraints and objectives. The objective could be to minimize total travel time, minimize fleet size, maximizing vehicle utilization, minimize transportation costs, reduce emissions while ensuring timely delivery and maintaining customer service level agreements (SLAs). Both pick-up and drop-off locations have capacity constraints, geographical proximity/constraints, service durations, time windows, precedence relationships and customer preferences. The fleet also has constraints such as limited capabilities, maximum load, maximum travel distance, or reduced emissions. Pickup and delivery use cases can be applied in various routing scenarios: Quick service food delivery, ride hailing, retail distribution, parcel delivery, intralogistics routing, school bus routing, and waste collection.

## Prepare cuOpt Container Image

```sh
docker pull nvcr.io/nvidia/cuopt/cuopt:24.11
docker tag nvcr.io/nvidia/cuopt/cuopt:24.11 nvcr.io/{NGC_ORG_ID}/cuopt:24.11
docker push nvcr.io/{NGC_ORG_ID}/cuopt:24.11
```

## Define the Function

1. [Create Function](https://nvcf.ngc.nvidia.com/create)
1. Custom Container
1. Function Details
   - Function Name: _nvidia-cuopt_
   - Function Description: _Dynamic rerouting, horizontal load-balancing, and robotic simulations, with sub second solver response times._
1. Container Details
   - Container: _nvcr.io/{NGC_ORG_ID}/cuopt_
   - Tag: _24.11_
1. Function Configuration
   - Inference Protocol: _HTTP_
   - Port: _8000_
   - Inference Endpoint: _/cuopt/cuopt_
   - Health Path: _/v2/health/ready_
   - Environment Variables:
     - `CUOPT_SERVER_PORT=8000`
     - `CUOPT_CHECK_CLIENT=False`
     - `CUOPT_RETURN_PERF_TIMES=True`
1. Save!

## Deploy Function Version

1. [Deploy Version](https://nvcf.ngc.nvidia.com/deployments/create)
1. Function Details:
   - Function Name: _nvidia-cuopt_
   - Function Version: _<Select_Latest_ID>_
1. Deployment Configuration:
   - GPU Type: _L40S_
1. Instance Type Settings:
   - Name: _gl40s_1.br25_2xlarge (L40S Default)_ (or similar)
1. Deployment Specifications:
   - Target Regions: _Any Region_
   - Clusters: _--_
   - Min Instances: _1_
   - Max Instances: _1_
   - Max Concurrency: _1_
1. Review Deployment
1. Deploy Version

## Launch Jupyterlab

1. create `.env` file:

```txt
NGC_API_KEY=nvapi-*
```

1. Launch notebook:

```sh
docker compose up
```
