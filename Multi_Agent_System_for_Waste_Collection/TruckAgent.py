import spade
import asyncio
import time
from colorama import init, Fore, Back
from spade.message import Message
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour
from spade.behaviour import CyclicBehaviour
from spade.template import Template

init(autoreset=True)


class TruckAgent(Agent):
    """
    Agent that represents the waste collection truck.

    This module defines the TruckAgent, representing a collection truck that responds to requests from bins, evaluates contracts,
    moves on a grid to pick up waste and delivers it to recycling centers using a Contract Net protocol.
    """
    def __init__(self, jid, password, initial_location=(5, 2), grid_size = 11):
        """
        Initialize a TruckAgent.

        Args:
            jid (str): JID that uniquely identifies the truck agent.
            password (str): Authentication password for the SPADE platform.
            initial_location (tuple[int, int], optional): Starting (x,y) position of the truck on the grid.
        """

        super().__init__(jid, password)
        self.initial_location = initial_location
    
    class Startup(OneShotBehaviour):
        """
        Initialize all dynamic state variables of the truck agent.

        Runs once when the agent starts and sets the initual values for fuel, waste capacity, location. contract state and operational flags. 
        It prepares the truck to participate in Contract Net negotiations, move across the grid, collect waste from bins and deliver it to a recycling center.

        Attributes:
            Current waste amounts for all types.
            Maximum waste capacity the truck can carry.
            Fuel and fuel capacity.
            Current grid location and initial movement targets.
            Flags used to control availability, contract acceptance and busy state.
            Tracking variables for the current bin and recycling center being served.

        Attributes:
            - current_waste_type_a (int):            Waste type A currently carried.
            - current_waste_type_b (int):            Waste type B currently carried.
            - current_waste_type_c (int):            Waste type C currently carried.
            - waste_capacity (int):                  Maximum amount of waste the truck can carry.
            - fuel (int):                            Current amount of fuel.
            - fuel_capacity (int):                   Maximum fuel capacity.
            - location (tuple[int, int]):            Current (x, y) position of the truck.
            - target_bin_location (tuple[int, int]): Location of the bin assigned for collection.
            - proposals_in_flight(dict):             Dictionary of proposals 
            - current_bin_jid (str | None):          JID of the assigned bin.
            - winning_center_jid (str ! None):       JID of the recycling center chosen for negotiation.
        """
        async def run(self):
            self.agent.current_waste_type_a = 0
            self.agent.current_waste_type_b = 0
            self.agent.current_waste_type_c = 0
            self.agent.waste_capacity = 20000
            self.agent.fuel = 602
            self.agent.fuel_capacity = 3000
            self.agent.location = self.agent.initial_location
            self.agent.target_bin_location = (0, 0)
            self.agent.conditions_to_accept_request = True
            self.agent.proposals_in_flight = {}
            self.agent.current_bin_jid = None
            self.agent.winning_center_jid = None
            
            
            await asyncio.sleep(1)

    class MonitorFuel(CyclicBehaviour):
        """
        Monitors the truck's fuel level and triggers refueling.

        Runs continuously and checks the current fuel percentage on every cycle and if the fuel drops below 20%, the truck becomes unavailable for new bin requests and refueling is activated.
        While low on fuel, the truck will:
            Refuse to participate in Contract Net bidding.
            Disable its ability to accept new requests.
            Prioritize restoring its capacity.
        
        Returns:
            None
        """
        async def run(self):
            threshold = 0.2
            if self.agent.fuel <= threshold * self.agent.fuel_capacity:
                self.agent.conditions_to_accept_request = False
                self.agent.add_behaviour(self.agent.Refuel())
                print(f"[{self.agent.name}] ⛽ Low on fuel!")
                await asyncio.sleep(1)

    class Refuel(OneShotBehaviour):
        """
        Reffils the truck's fuel until it reaches full capacity.

        Starts when the truck's fuel level drops below a critical threshold and simulates a refueling process by incrementing the fuel level until the maximum capacity is reached.
        Once it is complete, the truck becomes available.

        Returns:
            None
        """
        async def run(self):
            print(f"[{self.agent.name}] ⛽ Refueling...")
            
            while self.agent.fuel < self.agent.fuel_capacity:
                self.agent.fuel = min(self.agent.fuel + 367, self.agent.fuel_capacity)
                print(f"[{self.agent.name}] Fuel: {self.agent.fuel}/{self.agent.fuel_capacity}")
                await asyncio.sleep(1)
            
            self.agent.conditions_to_accept_request = True
            print(f"[{self.agent.name}] ✓ Refuel complete!")

    class ReceiveBinRequest(CyclicBehaviour):
        """
        Receives collection requests from bins and submits a proposal.

        Receives messages of type "bin_information" continuously during the simulation that contain the bin's waste levels, urgency level, location and capacity. 
        Upon receiving a request, the truck evaluates wether it is able to help based on its current state.
        If it is available, it computes a proposal score that reflect how suitable the truck is to handle the request, using the following factors:
            - Distance to the bin.
            - Remaining fuel.
            - Available waste capacity.
            - Urgency (normal/urgent).
            - Current load and operational status.

        A proposal is then sent to the bin or the request is ignored if the truck doesn't meet the criteria or isn't able to take care of it.

        Returns:
            None
        """
        async def run(self):
            msg = await self.receive(timeout=120)
            if not msg:
                await asyncio.sleep(0.5)
                return
            
            if msg and self.agent.conditions_to_accept_request:
                print(f"[{self.agent.name}] Request from {msg.sender}")
                # Extract information
                data = {}
                for line in msg.body.splitlines():
                    if ":" in line:
                        key, value = line.split(":", 1)
                        data[key.strip()] = value.strip()
                
                bin_jid = str(msg.sender)
                
                # Calculate Score
                score = 0
                
                a = self.agent.current_waste_type_a
                b = self.agent.current_waste_type_b
                c = self.agent.current_waste_type_c
                cap = self.agent.waste_capacity
                
                # Waste amounts from bin
                bin_a = int(data.get('Waste type A', 0))
                bin_b = int(data.get('Waste type B', 0))
                bin_c = int(data.get('Waste type C', 0))
                
                # Check if can fit at least SOME waste
                available_a = cap - a
                available_b = cap - b
                available_c = cap - c
                
                can_help = (available_a > 0 or available_b > 0 or available_c > 0) 
                
                if not can_help:
                    score = -999
                    print(f"[{self.agent.name}] Cannot help - Full, unavailable or BUSY")
                else:
                    # Base score for being able to help
                    score += 50
                    
                    # Bonus if can fit everything
                    if (a + bin_a <= cap and b + bin_b <= cap and c + bin_c <= cap):
                        score += 100
                        print(f"[{self.agent.name}] Can fit ALL waste!")
                    else:
                        # Partial capacity bonus
                        partial_score = (
                            min(available_a, bin_a) / max(bin_a, 1) +
                            min(available_b, bin_b) / max(bin_b, 1) +
                            min(available_c, bin_c) / max(bin_c, 1)
                        ) * 30
                        score += int(partial_score)
                        print(f"[{self.agent.name}] Can fit PARTIAL waste (score: {partial_score:.1f})")
                    
                    # Urgency bonus
                    urgency = data.get('Urgency', 'NORMAL')
                    if urgency == 'URGENT':
                        score += 150
                        print(f"[{self.agent.name}] URGENT request - priority bonus!")
                    
                    # Distance score (closer is better)
                    bin_loc_str = data.get('Location', '(0, 0)')
                    bin_loc_str = bin_loc_str.replace('(', '').replace(')', '').strip()
                    bin_x, bin_y = map(int, bin_loc_str.split(','))
                    
                    truck_x, truck_y = self.agent.location
                    distance = abs(bin_x - truck_x) + abs(bin_y - truck_y)
                    score += max(0, (20 - distance) * 5)
                    
                    # Fuel score
                    score += self.agent.fuel // 100
                
                print(f"[{self.agent.name}] Score: {score}")

                self.agent.proposals_in_flight.setdefault(bin_jid, {})
                self.agent.proposals_in_flight[bin_jid]['data'] = data
                self.agent.proposals_in_flight[bin_jid]['score'] = score
                self.agent.proposals_in_flight[bin_jid]['time'] = time.time()
                
                # Send proposal
                msg_proposal = Message(to=str(msg.sender))
                msg_proposal.set_metadata("type", "proposal")
                msg_proposal.body = f"Score: {score}\nTruck: {self.agent.name}"
                await self.send(msg_proposal)
                print(f"[{self.agent.name}] Proposal sent!")
            else:
                await asyncio.sleep(1)

    class HandleAccept(CyclicBehaviour):
        """
        Handles ACCEPT messages from bins and begins the assignment.

        When a bin selects a truck, it sends an ACCEPT message containing the bin's identifier. 
        This behaviour reacts to that message, sets the bin as the current target, retrieves the
        location and starts the movement phase towards the bin.

        Returns:
            None
        """
        async def run(self):
            msg = await self.receive(timeout=120)

            if not msg:
                await asyncio.sleep(0.5)
                return

            bin_jid = str(msg.sender)
            info = self.agent.proposals_in_flight.get(bin_jid)
            if not info:
                print("ACCEPT sem proposta correspondente -> ignorar")
                await asyncio.sleep(0.5)
                return

            bin_data = info.get('data') or {}
            print(f"[{self.agent.name}] ✓ ACCEPT received from {msg.sender}!")


            bin_loc_str = bin_data.get('Location', '(0, 0)')
            if bin_loc_str is None:
                bin_loc_str = '(0, 0)'

            try:
                bin_loc_str = bin_loc_str.replace('(', '').replace(')', '').strip()
                parts = [p.strip() for p in bin_loc_str.split(',') if p.strip() != '']
                if len(parts) == 2:
                    bin_x, bin_y = int(parts[0]), int(parts[1])
                else:
                    bin_x, bin_y = 0, 0
            except Exception:
                bin_x, bin_y = 0, 0

            self.agent.target_bin_location = (bin_x, bin_y)
            self.agent.current_bin_jid = bin_jid
            self.agent.conditions_to_accept_request = False
            self.agent.add_behaviour(self.agent.MoveToBin())
            self.agent.proposals_in_flight.pop(bin_jid, None)

            await asyncio.sleep(0.5)


    class HandleReject(CyclicBehaviour):
        """
        Handles REJECT messages from bins.

        Processes REJECT messages sent by bins when the truck is not selected. 
        Upon receiving a rejection, the truck discards the stored request data related to that bin and becomes free to other requests.

        Returns:
            None
        """
        async def run(self):
            msg = await self.receive(timeout=120)
            
            if msg:
                print(f"[{self.agent.name}] ✗ REJECT from {msg.sender}")
            
            await asyncio.sleep(0.5)

    class MoveToBin(OneShotBehaviour):
        """
        Moves the truck step-by-step toward the target bin location.

        It executes after the truck receives an ACCEPT message from the bin, moving the truck across the grid following a Manhattan distance strategy, consuming fuel as it travels.
        On each step, the behaviour:
            - Moves one tile closer to the bin's coordinates.
            - Decreases the truck's fuel level.
            - Checks whether it has reached the target location.
            - Notifies the bin upon arrival.
        
        Once the truck reaches the destination, the behaviour terminates and the waste transfer phase begins.

        Returns:
            None
        """
        async def run(self):
            print(f"[{self.agent.name}] 🚛 Moving to bin at {self.agent.target_bin_location}")
            
            target_x, target_y = self.agent.target_bin_location
            
            while self.agent.location != (target_x, target_y):
                current_x, current_y = self.agent.location
                
                # Move towards target
                if current_x < target_x:
                    self.agent.location = (current_x + 1, current_y)
                elif current_x > target_x:
                    self.agent.location = (current_x - 1, current_y)
                elif current_y < target_y:
                    self.agent.location = (current_x, current_y + 1)
                elif current_y > target_y:
                    self.agent.location = (current_x, current_y - 1)
                
                self.agent.fuel -= 1

                await asyncio.sleep(1)
            
            self.agent.add_behaviour(self.agent.InformBinTruckArrival())

    class InformBinTruckArrival(OneShotBehaviour):
        """
        Notifies the bin that the truck has arrived at its location.

        After reaching the bin, once per collection cycle, this behaviour sends a message of type "arrival" to the specified bin.
        This notification allows the bin to start the waste-transfer phase by triggering its own TransferWasteRequest behaviour.

        Returns:
            None
        """
        async def run(self):
            msg = Message(to=self.agent.current_bin_jid)
            msg.set_metadata("type", "arrival")
            msg.body = "I have arrived"
            
            await self.send(msg)
            print(f"[{self.agent.name}] ✓ Arrived at bin!")

    class TransferWasteWithBin(CyclicBehaviour):
        """
        Handles the waste transfer process between the truck and the bin.

        After arriving at the bin, the truck receives a message containing the current quantitites of each waste type stored in the bin.
        This behaviour computes how much waste the truck can load based on its remaining capacity and updates the truck's internal waste counters.
        Any waste exceeding the truck's available capacity is considered leftover and is sent back to the bin with a follow-up message. 
        This allows the bin to retain the uncollected waste and request help again later.
        After a successful transfer, the truck:
            - Updates its internal waste load.
            - Finalizes the collection phase.
            - Becomes ready to negotiate with recycling centers.
        
        This behaviour triggers once per transfer, whenever the bin sends the message containing the waste information.

        Returns:
            None
        """     
        async def run(self):
            res = await self.receive(timeout=120)
            
            if res:
                print(f"[{self.agent.name}] Transferring waste...")
                
                # Extract data
                data = {}
                for line in res.body.splitlines():
                    if ":" in line:
                        key, value = line.split(":", 1)
                        data[key.strip()] = value.strip()
                
                cap = self.agent.waste_capacity
                
                # Calculate what can be taken
                bin_a = int(data.get('Waste type A', 0))
                bin_b = int(data.get('Waste type B', 0))
                bin_c = int(data.get('Waste type C', 0))
                
                # Space available
                space_a = cap - self.agent.current_waste_type_a
                space_b = cap - self.agent.current_waste_type_b
                space_c = cap - self.agent.current_waste_type_c
                
                # Take what fits
                taken_a = min(bin_a, space_a)
                taken_b = min(bin_b, space_b)
                taken_c = min(bin_c, space_c)
                
                self.agent.current_waste_type_a += taken_a
                self.agent.current_waste_type_b += taken_b
                self.agent.current_waste_type_c += taken_c
                
                # Calculate leftovers
                a_left = bin_a - taken_a
                b_left = bin_b - taken_b
                c_left = bin_c - taken_c
                
                print(f"[{self.agent.name}] Took: A={taken_a}, B={taken_b}, C={taken_c}")
                print(f"[{self.agent.name}] Left: A={a_left}, B={b_left}, C={c_left}")
                
                # Send leftovers back
                msg = Message(to=str(res.sender))
                msg.set_metadata("type", "transferleftovers")
                msg.body = (
                    f"Left over waste type A: {a_left}\n"
                    f"Left over waste type B: {b_left}\n"
                    f"Left over waste type C: {c_left}\n"
                )
                
                await self.send(msg)
                print(f"[{self.agent.name}] ✓ Transfer complete!")

                self.agent.conditions_to_accept_request = True
                

    class MonitorTruckRemainCapacity(CyclicBehaviour):
        """
        Monitors remaining capacity and triggers unloading to recycling centers when needed.

        Periodically checks the truck's current load for each waste type and, if any type reaches the configured threshold
        fraction of the truck's capacity, marks the truck unavailable for new bin requests and enqueues the behaviour that
        starts negotiation with recycling centers.

        Behavioural effects:
            - Sets self.agent.conditions_to_accept_request to False to prevent new proposals.
            - Adds the SignalRecyclingCenter behaviour to initiate RC negotiation.
            - Logs a notice that the truck is almost full.

        Configuration:
            - threshold is a fraction (0..1) of waste_capacity; default used here is 0.2 (20%).

        Returns:
            None
        """
        async def run(self):
            threshold = 0.7
            a = self.agent.current_waste_type_a 
            b = self.agent.current_waste_type_b 
            c = self.agent.current_waste_type_c 
            capacity = self.agent.waste_capacity

            if a >= threshold * capacity or b >= threshold * capacity or c >= threshold * capacity:
                self.agent.conditions_to_accept_request = False
                self.agent.add_behaviour(self.agent.SignalRecyclingCenter())
                print(f"[{self.agent.name}] Truck almost full!")
                await asyncio.sleep(1)



    class SignalRecyclingCenter(OneShotBehaviour):
        """
        Requests proposals from recycling centers to unload collected waste.

        Triggers when the truck becomes full or after completing a pickup operation. It initiates a second Contract Net negotiation, this time with recycling centers.
        The truck broadcasts a request message to all recycling centers, including:
            - The current amounts of each waste type.
            - The truck's location.
            - Metadata specifying the reqiest type ("truck_information").
        
        Recycling centers respond with proposals containing a score that reflects their ability to accept the truck's waste load. 
        After this behaviour executes, the truck awaits these proposals in the next negotiation phase.

        Returns:
            None
        """
        async def run(self):
            for i in range(2):
                msg = Message(to=f"RCA{i}@localhost")
                msg.set_metadata("performative", "request")
                msg.set_metadata("type", "truck_information")
                msg.body = (
                    f"Waste type A: {self.agent.current_waste_type_a}\n"
                    f"Waste type B: {self.agent.current_waste_type_b}\n"
                    f"Waste type C: {self.agent.current_waste_type_c}\n"
                    f"Location: {self.agent.location}\n"
                )
                
                await self.send(msg)
                print(f"[{self.agent.name}] Request sent to RCA{i}")
                await asyncio.sleep(0.5)

    class EvaluateProposalsFromRC(CyclicBehaviour):
        """
        Evaluates proposals from recycling centers ans selects the best one.

        After signaling recycling centers, the truck waits for proposals, each containing a score reflecting the processing availability, distance, current load, 
        and remaining capacity at the recycling center.
        This behaviour:
            - Collects all proposals within the time frame.
            - Selects the center with the highest score.
            - Sends an ACCEPT to the chosen center.
            - Send REJECT to all the other centers.
            - Stores the chosen center's JID and awaits its location message.

        This behaviour completes the Contract Net negotiation for unloading and transitions the truck to the movement phase towards the selected center.

        Returns:
            None
        """
        async def run(self):
            proposals = []
            
            for _ in range(2):
                msg = await self.receive(timeout=20)
                if msg:
                    proposals.append(msg)
                    print(f"[{self.agent.name}] RC proposal from {msg.sender}")
            
            if len(proposals) < 2:
                print(Fore.BLACK + Back.RED + f"[{self.agent.name}] Not enough RC proposals!")
                return
            
            best_rc_msg = self.select_best(proposals)
            self.agent.winning_center_jid = str(best_rc_msg.sender)
            
            # Send ACCEPT
            msg_accept = Message(to=self.agent.winning_center_jid)
            msg_accept.set_metadata("type", "rc_accept")
            msg_accept.body = "ACCEPT - You won!"
            await self.send(msg_accept)
            print(Fore.GREEN + f"[{self.agent.name}] ACCEPT to {best_rc_msg.sender}")
            
            # Send REJECT
            for proposal in proposals:
                if proposal.sender != best_rc_msg.sender:
                    msg_reject = Message(to=str(proposal.sender))
                    msg_reject.set_metadata("type", "rc_reject")
                    msg_reject.body = "REJECT"
                    await self.send(msg_reject)
                    print(Fore.RED + f"[{self.agent.name}] REJECT to {proposal.sender}")
            
            await asyncio.sleep(5)
        
        def select_best(self, proposals_list):
            best_msg = None
            best_score = -999999
            
            for msg in proposals_list:
                lines = msg.body.split('\n')
                for line in lines:
                    if line.startswith("Score:"):
                        score = int(float(line.split(":")[1].strip()))
                        if score > best_score:
                            best_score = score
                            best_msg = msg
                        break
            
            print(f"[{self.agent.name}] Best RC: {best_score}")
            return best_msg

    class MoveToRC(CyclicBehaviour):
        """
        Moves the truck towards the selected recycling center.

        This behaviour is executed after the truck received confirmation from a recycling center and the truck then moves across the grid, 
        updating its position and fuel levels on each tick.
        Once the truck reaches the target center location, this behaviour:
            - Stops movement.
            - Notifies the recycling center of its arrival.
            - Triggers the waste transfer behaviour.

        Returns:
            None
        """
        async def run(self):
            msg = await self.receive(timeout=120)
            
            if msg:
                print(f"[{self.agent.name}] 🚛 Moving to RC...")
                
                data = {}
                for line in msg.body.splitlines():
                    if ":" in line:
                        key, value = line.split(":", 1)
                        data[key.strip()] = value.strip()
                
                rc_loc_str = data.get('Location', '(2, 3)')
                rc_loc_str = rc_loc_str.replace('(', '').replace(')', '').strip()
                rc_x, rc_y = map(int, rc_loc_str.split(','))
                
                while self.agent.location != (rc_x, rc_y):
                    current_x, current_y = self.agent.location
                    
                    if current_x < rc_x:
                        self.agent.location = (current_x + 1, current_y)
                    elif current_x > rc_x:
                        self.agent.location = (current_x - 1, current_y)
                    elif current_y < rc_y:
                        self.agent.location = (current_x, current_y + 1)
                    elif current_y > rc_y:
                        self.agent.location = (current_x, current_y - 1)
                    
                    self.agent.fuel -= 1
                
                    await asyncio.sleep(1)
                
                self.agent.add_behaviour(self.agent.InformRCTruckArrival())

    class InformRCTruckArrival(OneShotBehaviour):
        """
        Notifies the selected center that the truck has arrived.

        This behaviour sends a message to the chosen center to confirm that the truck has reached its location and is ready to begin the waste transfer process.

        Returns:
            None
        """
        async def run(self):
            if self.agent.winning_center_jid:
                msg = Message(to=self.agent.winning_center_jid)
                msg.set_metadata("type", "truck_arrival")
                msg.body = "I have arrived"
                
                await self.send(msg)
                print(f"[{self.agent.name}] ✓ Arrived at RC!")

    class TransferWasteWithRCRequest(CyclicBehaviour):
        """
        Sends the truck's current waste load to the center.

        After arriving at the recycling center, the truck sends the quantities of each waste type it is carrying. 
        The recycling center will process the information and update its internal load, beggining the unloading phase.

        Returns:
            None
        """
        async def run(self):
            res = await self.receive(timeout=120)
            
            if res:
                msg = Message(to=self.agent.winning_center_jid)
                msg.set_metadata("type", "waste_information")
                msg.body = (
                    f"Waste type A: {self.agent.current_waste_type_a}\n"
                    f"Waste type B: {self.agent.current_waste_type_b}\n"
                    f"Waste type C: {self.agent.current_waste_type_c}\n"
                )
                
                await self.send(msg)

    class TransferWasteWithRCResponse(CyclicBehaviour):
        """
        Handles the recycling center's confirmation after the waste transfer.

        Receives the final response from the center after the truck has unloaded its waste. 
        The message typically confirms that the transfer was completed with success. 
        Once received, the truck resets its internal state related to the delivery process, clears the reference to the recycling center it was serving 
        and becomes available for new requests.

        Returns:
            None
        """
        async def run(self):
            res = await self.receive(timeout=120)
            
            if res:
                self.agent.current_waste_type_a = 0
                self.agent.current_waste_type_b = 0
                self.agent.current_waste_type_c = 0
                
                print(f"[{self.agent.name}] ✓ RC transfer complete! Truck empty.")
                self.agent.order_accepted = False

    async def setup(self):
        """
        Configures the truck agent by registering all behaviours and templates.

        Runs automatically when the agent starts, loads all behaviours required for the truck's operation, including Startup, MonitoFuel, Refuel, ReceiveBinRequest, 
        HandleAccept, HandleReject, MoveToBin, InformBinTruckArrival, TransferWasteWithBinRequest/Response, SignalRecyclingCenter, EvaluateProposalsFromRC, MoveToRC,
        InformRCTruckArrival and TransferWasteWithRCRequest/Response.

        The message templates are configured to ensure each behaviour reacts only to messages with the correct metadata type.
        """
        print(f"Starting {self.name} at {self.initial_location}...")
        self.add_behaviour(self.Startup())
        self.add_behaviour(self.MonitorFuel())
        self.add_behaviour(self.MonitorTruckRemainCapacity())
        
        # Bin templates
        t1 = Template()
        t1.set_metadata("type", "bin_information")
        self.add_behaviour(self.ReceiveBinRequest(), t1)
        
        t_accept_bin = Template()
        t_accept_bin.set_metadata("type", "accept")
        self.add_behaviour(self.HandleAccept(), t_accept_bin)
        
        t_reject_bin = Template()
        t_reject_bin.set_metadata("type", "reject")
        self.add_behaviour(self.HandleReject(), t_reject_bin)
        
        t2 = Template()
        t2.set_metadata("type", "transferData")
        self.add_behaviour(self.TransferWasteWithBin(), t2)
        
        # RC templates
        t_rc_proposal = Template()
        t_rc_proposal.set_metadata("type", "rc_proposal")
        self.add_behaviour(self.EvaluateProposalsFromRC(), t_rc_proposal)
        
        t3 = Template()
        t3.set_metadata("type", "RCA_location")
        self.add_behaviour(self.MoveToRC(), t3)
        
        t4 = Template()
        t4.set_metadata("type", "transfer_ready")
        self.add_behaviour(self.TransferWasteWithRCRequest(), t4)
        
        t5 = Template()
        t5.set_metadata("type", "transfer_complete")
        self.add_behaviour(self.TransferWasteWithRCResponse(), t5)
