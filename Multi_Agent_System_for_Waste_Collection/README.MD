# **Multi-Agent Decentralized Waste Collection and Recycling System with Spade**

A simulation framework for autonomous agents built with [Spade](https://spade-mas.readthedocs.io/), enabling developers to create, test, analyze and simulate multi-agent scenarios in a realistic environment.

## **Overview**

This project uses Spade (Smart Python Agent Development Environment) to simulate a waste collection and recycling system. Spade provides a platform for developing multi-agent systems using XMPP server for agent communication, allowing for distributed, scalable, and realistic agent interactions in waste management scenarios.

## **Features**

- **Passive Waste Generation**: Bins simulate citizen behavior without excessive computation.
- **Threshold-Based Signaling**: Intelligent waste level monitoring and alerting.
- **Decentralized Waste Management**: Smart bins autonomously signal collection needs.
- **Dynamic Truck Dispatching**: Trucks respond to bin requests and coordinate deliveries.
- **Recycling Center Management**: Central processing facility manages incoming waste streams.
- **Multi-Agent Coordination**: Communication between bins, trucks, and recycling centers.
- **Real-time Visualization**: Simple vizualization of agents interaction in real time.
- **XMPP-Based Communication**: Reliable agent-to-agent messaging protocol provided by spade.

## **Prerequisites**

- Python 3.8 or higher
- pip package manager

## **Installation**

Install Spade via pip:
```bash
python -m pip install spade
```

Or clone the repository:
```bash
git clone <repo-url>
cd <project-directory>
pip install -r requirements.txt
```

## **System Architecture**

The simulation consists of three main agent types that work together to manage waste collection and recycling:

### 1. SmartBinAgent (`SmartBinAgent.py`)
- Passively generates waste to simulate citizen behavior without excessive computational overhead
- Monitors waste levels against a defined threshold
- Signals nearby trucks when the threshold is reached
- Manages bin capacity and waste accumulation

### 2. TruckAgent (`TruckAgent.py`)
- Receives collection requests from smart bins
- Transports waste from bins to the recycling center
- Coordinates with recycling center for delivery acceptance
- Manages truck capacity, routing and fuel

### 3. RecyclingCenterAgent (`RecyclingCenter.py`)
- Receives delivery requests from trucks
- Verifies capacity to accept incoming waste quantities
- Passively processes and recycles accumulated waste
- Manages center capacity and throughput

## Quick Start

Run the simulation:
```bash
python simulation.py
```

The simulation will initialize all agents and begin the waste collection cycle. Use the visualization helper function to monitor agent interactions in real-time.

## Project Structure

```
.
├── SmartBinAgent.py            # Smart bin agent implementation
├── TruckAgent.py               # Waste collection truck agent
├── RecyclingCenterAgent.py     # Recycling center agent
├── simulation.py               # Main simulation
├── VisualizationHelper.py      # Visualization utilities
└── README.MD                   # Project dependencies
```

## Workflow

1. **Waste Generation**: Smart bins passively accumulate waste over time, simulating citizen disposal behavior
2. **Threshold Detection**: When a bin's waste level reaches the configured threshold, it broadcasts a collection request
3. **Truck Response**: Available trucks receive the request and coordinate to handle the collection
4. **Waste Exchange**: Truck collects waste from the bin
5. **Capacity Check**: Trucks communicate with the recycling center to verify acceptance capacity
6. **Processing**: Recycling center accepts the delivery and passively processes the waste
7. **Cycle Continues**: The system continuously operates as bins generate more waste

### Configuration

You can adjust simulation parameters such as:
- Agents starting locations
- Bin waste generation rate
- Waste threshold levels
- Truck capacity
- Truck initial fuel, fuel consumption, fuel capacity, refuel speed.
- Recycling center processing speed
- Recycling center capacity
- Number of bins, trucks, and recycling centers

## Usage

### Running the Simulation

```bash
python simulation.py
```

### Monitoring the System

The visualization helper provides real-time insights into:
- Bin, Truck and Recycling center locations
- Agent communication and exchanged messages

## Documentation

For detailed documentation on Spade features and APIs, visit:
- [Spade Documentation](https://spade-mas.readthedocs.io/)