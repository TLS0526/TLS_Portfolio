import spade
import asyncio
import random
from spade.message import Message
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour
from spade.behaviour import CyclicBehaviour
from spade.template import Template


class RecyclingCenterAgent(Agent):
    """
    Recycling center agent for a multi-agent smart waste management system.

    Defines the RecyclingCenterAgent, which receives requests from collection trucks, evaluates its available processing capacity, participates in a Contract Net protocol,
    provides its location to the selected truck, and performs the waste transfer and processing operations.
    """
    def __init__(self, jid, password, initial_location):
        """
        Initialize a RecyclingCenterAgent.

        Args:
            jid (str): JID that uniquely identifies the recycling center agent.
            password (str): Authentication password for the SPADE platform.
            initial_location (tuple[int, int]): Initial (x, y) position of the recycling center on the grid.
        """
        super().__init__(jid, password)
        self.initial_location = initial_location
    
    class Startup(OneShotBehaviour):
        """
        Initialize all dynamic state variables of the recycling center.

        Runs once when the agent starts and sets up the internal processing counters for each waste type, as well as the total processing capacity of the facility. 
        It also registers the center's fixed location and resets the active truck-assignment state.

        Attributes:
            - current_waste_type_a_processing: Amount of type A waste currently being processed.
            - current_waste_type_b_processing: Amount of type B waste currently being processed.
            - current_waste_type_c_processing: Amount of type C waste currently being processed.
            - capacity:                        Maximum amount of waste the center can process simultaneously.
            - location:                        Fixed (x, y) position of the recycling center.
            - current_truck_jid:               Identifier of the truck currently assigned to the center.
        """
        async def run(self):
            self.agent.current_waste_type_a_processing = 0
            self.agent.current_waste_type_b_processing = 0
            self.agent.current_waste_type_c_processing = 0
            self.agent.capacity = 50000
            self.agent.location = self.agent.initial_location
            self.agent.current_truck_jid = None

    class ReceiveTruckRequest(CyclicBehaviour):
        """
        Handles incoming requests from truck agents and computes a proposal score.

        Checks messages of type "truck_information" sent by trucks looking for a recycling center to unload their current waste, runs continuously.
        When a request is received, the behaviour extracts waste quantities, truck location and other relevant data from the message.
        It then computes a score based on:
            - Whether the center has enough remaining capacity to accept the waste.
            - The distance between the truck and the recycling center.
            - The current processing load of the center.

        If the request is valid,  a proposal is generated and sent back to the truck, if not, a negative score is sent.

        Returns:
            None
        """
        async def run(self):
            msg = await self.receive(timeout=120)
            if not msg:
                await asyncio.sleep(0.5)
                return

            if msg:
                print(f"[{self.agent.name}] Request from {msg.sender}")
                
                # Extract information
                data = {}
                for line in msg.body.splitlines():
                    if ":" in line:
                        key, value = line.split(":", 1)
                        data[key.strip()] = value.strip()
                
                # Calculate Score
                score = 0
                
                # Capacity check
                a = self.agent.current_waste_type_a_processing
                b = self.agent.current_waste_type_b_processing
                c = self.agent.current_waste_type_c_processing
                cap = self.agent.capacity
                
                can_accept = (
                    a + int(data.get('Waste type A', 0)) <= cap and
                    b + int(data.get('Waste type B', 0)) <= cap and
                    c + int(data.get('Waste type C', 0)) <= cap
                )
                
                if can_accept:
                    score += 100
                else:
                    score = -999

                
                # Distance score
                truck_loc_str = data.get('Location', '(0, 0)')
                truck_loc_str = truck_loc_str.replace('(', '').replace(')', '').strip()
                truck_x, truck_y = map(int, truck_loc_str.split(','))
                
                rc_x, rc_y = self.agent.location
                distance = abs(truck_x - rc_x) + abs(truck_y - rc_y)
                score += max(0, (20 - distance) * 5)
                
                # Current load score
                total_processing = a + b + c
                load_score = max(0, (self.agent.capacity - total_processing) // 1000)
                score += load_score
                
                print(f"[{self.agent.name}] Score: {score}")
                
                # Send proposal
                msg_proposal = Message(to=str(msg.sender))
                msg_proposal.set_metadata("type", "rc_proposal")
                msg_proposal.body = f"Score: {score}\nCenter: {self.agent.name}"
                await self.send(msg_proposal)
                print(f"[{self.agent.name}] Proposal sent!")
            else:
                await asyncio.sleep(1)

    
    class HandleAccept(CyclicBehaviour):
        """
        Handles ACCEPT messages from trucks.

        When a truck choses the recycling center, this behaviour stores the truck's JID and replies with
        the center's location so the truck can begin moving towards it.

        Returns:
            None
        """
        async def run(self):
            msg = await self.receive(timeout=120)
            
            if msg:
                print(f"[{self.agent.name}] ACCEPT received from {msg.sender}!")
                
                # Save winning truck JID
                self.agent.current_truck_jid = str(msg.sender)
                
                # Send location to truck
                res = Message(to=self.agent.current_truck_jid)
                res.set_metadata("type", "RCA_location")
                res.body = f"Location: {self.agent.location}"
                
                await self.send(res)
                print(f"[{self.agent.name}] Location sent to {msg.sender}")
            
            await asyncio.sleep(0.5)


    class HandleReject(CyclicBehaviour):
        """
        Handles REJECT messages sent by truck.

        This behaviour simply listens for rejection notifications from truck agents and logs them, allowing the
        recycling center to ignore that interaction and remain available for other proposals.

        Returns:
            None
        """
        async def run(self):
            msg = await self.receive(timeout=120)
            
            if msg:
                print(f"[{self.agent.name}] REJECT received from {msg.sender}")
            
            await asyncio.sleep(0.5)


    class ReceiveTruckArrival(CyclicBehaviour):
        """
        Handle arrival notifications from the truck.

        Waits for a message indicating that the assigned truck has reached the recycling center and when
        one is received, this behaviour replies confirming that the center is ready to begin the waste transfer process.

        Returns:
            None
        """
        async def run(self):
            res = await self.receive(timeout=120)

            if res:
                print(f"[{self.agent.name}] Truck {res.sender} arrived!")
                
                # Send confirmation
                msg = Message(to=str(res.sender))
                msg.set_metadata("type", "transfer_ready")
                msg.body = "Ready to transfer!"

                await self.send(msg)
            else: 
                await asyncio.sleep(1)

    
    class TransferWasteWithTruck(CyclicBehaviour):
        """
        Receives waste from the arriving truck and updates processing levels.

        Processes the waste sent by the truck, adds the received amounts to the center's internal processing
        counters and sends back a confirmation message indicating that the transfer is complete.

        Returns:
            None
        """
        async def run(self):
            res = await self.receive(timeout=120)

            if res:
                print(f"[{self.agent.name}] Transferring waste from {res.sender}")

                # Extract waste data
                data = {}
                for line in res.body.splitlines():
                    if ":" in line:
                        key, value = line.split(":", 1)
                        data[key.strip()] = value.strip()

                # Add to processing
                self.agent.current_waste_type_a_processing += int(data.get("Waste type A", 0))
                self.agent.current_waste_type_b_processing += int(data.get("Waste type B", 0))
                self.agent.current_waste_type_c_processing += int(data.get("Waste type C", 0))

                # Confirm transfer
                msg = Message(to=str(res.sender))
                msg.set_metadata("type", "transfer_complete")
                msg.body = "Transfer complete"

                await self.send(msg)

                print(f"[{self.agent.name}] Transfer complete!")
                print(f"  Processing A: {self.agent.current_waste_type_a_processing}")
                print(f"  Processing B: {self.agent.current_waste_type_b_processing}")
                print(f"  Processing C: {self.agent.current_waste_type_c_processing}")
                
                # Reset current truck
                self.agent.current_truck_jid = None

    class RecyclingProcess(CyclicBehaviour):
        """
        Gradually processes the waste stored at the recycling center.

        Runs continuously and simulates the recycling of waste by reducing the amounts of each waste type over time.
        It prints the current processing status whenever waste remains to be treated.

        Returns:
            None
        """
        async def run(self):
            processing_waste_type_a = random.randint(650,950)
            processing_waste_type_b = random.randint(800, 1200)
            processing_waste_type_c = random.randint(750, 1100)
            self.agent.current_waste_type_a_processing = max(self.agent.current_waste_type_a_processing - processing_waste_type_a, 0)
            self.agent.current_waste_type_b_processing = max(self.agent.current_waste_type_b_processing - processing_waste_type_b, 0)
            self.agent.current_waste_type_c_processing = max(self.agent.current_waste_type_c_processing - processing_waste_type_c, 0)
            
            if (self.agent.current_waste_type_a_processing > 0 or
                self.agent.current_waste_type_b_processing > 0 or
                self.agent.current_waste_type_c_processing > 0):
                print(f"[{self.agent.name}] ♻️  RECYCLING...")
                print(f"  A: {self.agent.current_waste_type_a_processing}")
                print(f"  B: {self.agent.current_waste_type_b_processing}")
                print(f"  C: {self.agent.current_waste_type_c_processing}")
                print("-" * 40)
            
            await asyncio.sleep(1)
    
    
    async def setup(self):
        """
        Registers all behaviours and message templates for the recycling center.

        This method runs automatically when the agent starts. 
        It loads all behaviours responsible for receiving truck requests, handling messages, processing truck arrivals, mananing waste transfers and performing continuous recycling. 
        """
        print(f"Starting {self.name}...")
        self.add_behaviour(self.Startup())
        self.add_behaviour(self.RecyclingProcess())

        # Template para receber pedidos do truck
        t1 = Template()
        t1.set_metadata("type", "truck_information")
        self.add_behaviour(self.ReceiveTruckRequest(), t1)

        # Templates para Contract Net (NOVO!)
        t_accept = Template()
        t_accept.set_metadata("type", "rc_accept")
        self.add_behaviour(self.HandleAccept(), t_accept)

        t_reject = Template()
        t_reject.set_metadata("type", "rc_reject")
        self.add_behaviour(self.HandleReject(), t_reject)

        # Template para truck arrival
        t2 = Template()
        t2.set_metadata("type", "truck_arrival")
        self.add_behaviour(self.ReceiveTruckArrival(), t2)
    
        # Template para transfer
        t3 = Template()
        t3.set_metadata("type", "waste_information")
        self.add_behaviour(self.TransferWasteWithTruck(), t3)
