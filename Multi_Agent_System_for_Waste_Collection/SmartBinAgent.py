# smartbinagent
import spade
from colorama import init, Fore, Back
import asyncio
from spade.agent import Agent
from spade.message import Message
from spade.behaviour import OneShotBehaviour
from spade.behaviour import CyclicBehaviour
from spade.template import Template
import random

init(autoreset=True)


class SmartBinAgent(Agent):
    """
    Agent that simulates a smart waste bin.

    Periodically and randomly generates different types of waste, monitors its fill level and requests collection from nearby truck agents
    when the threshold is exceeded. It can issue normal or urgent requests and handles the full negotiation and transfer process.
    """

    def __init__(self, jid, password, initial_location, grid_center):
        """
        Initialize a Smart bin agent.

        Args:
            jid (str): Unique identifier for the agent.
            password (str): Password used for authentication in the Spade platform.
            initial_location (tuple[int, int]): Initial (x, y) position of the bin on the grid.
            waste_generation_rate (tuple[int, int, int]): Amount of waste generated per tick for each type (A,B,C).
        """
        super().__init__(jid, password)
        self.initial_location = initial_location
        self.grid_center = grid_center

    
    class Startup(OneShotBehaviour):
        """
        Initialize all dynamic attributes when the agent is created.

        Attributes:
            - initial_location (tuple[int, int]): Fixed (x, y) position of the bin on the grid.
            - waste_type_a_generation_rate (int): Amount of waste type A generated per tick.
            - waste_type_b_generation_rate (int): Amount of waste type B generated per tick.
            - waste_type_c_generation_rate (int): Amount of waste type C generated per tick.
            - winning_truck_jid (None | str):     Jid of the truck who won the contract
            - is_requesting_help(bool):           Flag that indicates if the bin has enough trash to signal the truck
            - urgent_mode(bool):                  Flag that indicates what type of singal the bin has send to truck
        """

        async def run(self):
            self.agent.waste_type_a = 0
            self.agent.waste_type_b = 0
            self.agent.waste_type_c = 0
            self.agent.location = self.agent.initial_location
            self.agent.waste_capacity = 10000
            self.agent.winning_truck_jid = None
            self.agent.is_requesting_help = False  
            self.agent.urgent_mode = False  


    class GenerateWaste(CyclicBehaviour):  
        """
        Periodically generate a random ammount of waste inside the smart bin.

        Runs continuously (every 1 second) and increases the levels of all waste types. 
        It simulates the waste accumulation over time.

        Returns:
            None
        """

        async def run(self):     
            x, y = self.agent.location
            distance = abs(x - self.grid_center) + abs(y - self.grid_center)
            max_distance = 10
            proximity = max(0.2, 1 - (distance/max_distance))

            waste_a = random.randint(35, 150) * proximity
            waste_b = random.randint(83, 450) * proximity
            waste_c = random.randint(65, 380) * proximity

            self.agent.waste_type_a += int(waste_a)         
            self.agent.waste_type_b += int(waste_b)         
            self.agent.waste_type_c += int(waste_c)      
        
            await asyncio.sleep(1)                
    

    class MonitorWaste(CyclicBehaviour):
        """
        Continuously monitor the bin's fill level and trigger collection requests.

        Evaluates the percentage of waste capacity used for each waste type and determines if the bin should request help
        from truck agents. Runs every 1 second.
        Monitored thresholds:
            - Normal request: triggered when fill level reaches 20%.
            - Urgent request: triggered when fill level reaches 80% or when overflow occurs.
        
        When a threshold is reached, it activates the correspondent request, sets flags to prevent duplicate requests and
        starts the negotiation with available trucks.

        Returns:
            None
        """

        async def run(self):
            threshold_normal = 0.4   # 40% - pedido normal
            threshold_urgent = 0.8   # 80% - pedido urgente
            
            total_a = self.agent.waste_type_a / self.agent.waste_capacity
            total_b = self.agent.waste_type_b / self.agent.waste_capacity
            total_c = self.agent.waste_type_c / self.agent.waste_capacity
            
            max_fill = max(total_a, total_b, total_c)

            # Verifica se já ultrapassou a capacidade
            if max_fill >= 1.0:
                print(Back.RED + Fore.WHITE + f"[{self.agent.name}] OVERFLOW! Capacity exceeded: {max_fill*100:.1f}%")
                self.agent.urgent_mode = True

            # Sistema de pedidos baseado em urgência
            if not self.agent.is_requesting_help:
                if max_fill >= threshold_urgent:
                    print(Back.RED + Fore.WHITE + f"[{self.agent.name}] URGENT request! Fill level: {max_fill*100:.1f}%")
                    self.agent.urgent_mode = True
                    self.agent.is_requesting_help = True
                    self.agent.add_behaviour(self.agent.SignalTruck())
                
                elif max_fill >= threshold_normal:
                    print(Fore.YELLOW + f"[SBA] Regular request. Fill level: {max_fill*100:.1f}%")
                    self.agent.urgent_mode = False
                    self.agent.is_requesting_help = True
                    self.agent.add_behaviour(self.agent.SignalTruck())
            
            await asyncio.sleep(1)

    
    class SignalTruck(OneShotBehaviour):
        """
        Send a collection request to all truck agents.

        Its triggered when the smart bin detects that its fill level has reached either the normal or ugent threshold. 
        Sends a message to every truck agent including the current waste amounts, location, capacity and urgency level.

        Runs once per request cycle and doesn't repeat unless the bin becomes full again.

        Returns:
            None
        """

        async def run(self):
            urgency_level = "URGENT" if self.agent.urgent_mode else "NORMAL"
            
            for i in range(2):
                msg = Message(to=f"TA{i}@localhost")
                msg.set_metadata("type", "bin_information")
                msg.set_metadata("Urgency", urgency_level)  # Novo metadata
                msg.body = (
                    f"Urgency: {urgency_level}\n"
                    f"Waste type A: {self.agent.waste_type_a}\n"
                    f"Waste type B: {self.agent.waste_type_b}\n"
                    f"Waste type C: {self.agent.waste_type_c}\n"
                    f"Location: {self.agent.location}\n"
                    f"Capacity: {self.agent.waste_capacity}\n"
                )
                
                await self.send(msg)
                print(Fore.YELLOW + f"[{self.agent.name}] {urgency_level} request sent to TA{i}!")
                await asyncio.sleep(1)


    class EvaluateProposals(CyclicBehaviour):
        """
        Evaluate and select the best truck agent available.

        Implements the decision phase of a Contract Net protocol. After the bin sends a collection request, it waits for proposals
        from available truck agents containing a computed score that shows how suitable the truck is to handle the request.
        Computed score: remaining capacity, fuel level, distance, urgency handling.
        After collecting the proposals it selects the one with the highest score and sends an accept message to the chosen truck 
        as well as a reject message to all other trucks. Resets internal request flags when no proposals arrive.
        If no truck responds within the time frame, the bin requests help again, it runs periodically until a truck is successfully selected.

        Returns:
            None
        """

        async def run(self):

            proposals = []
            
            for _ in range(2):
                msg = await self.receive(timeout=20)
                if msg:
                    proposals.append(msg)
                    print(Fore.CYAN + f"[{self.agent.name}] Received proposal from {msg.sender}")
            
            if len(proposals) < 1:
                print(Fore.BLACK + Back.RED + f"[{self.agent.name}] No proposals received! Retrying...")
                self.agent.is_requesting_help = False  # Permite nova tentativa
                return

            # Escolhe o melhor
            best_truck_msg = self.select_best(proposals)
            
            if best_truck_msg is None:
                print(Fore.RED + f"[{self.agent.name}] All trucks rejected the request!")
                self.agent.is_requesting_help = False
                return
            
            # Guarda o vencedor
            self.agent.winning_truck_jid = str(best_truck_msg.sender)

            # Envia ACCEPT
            msg_accept = Message(to=self.agent.winning_truck_jid)
            msg_accept.set_metadata("type", "accept")
            msg_accept.body = "ACCEPT - You won the contract!"
            await self.send(msg_accept)
            print(Fore.GREEN + f"[{self.agent.name}] ACCEPT sent to {best_truck_msg.sender}")

            # Envia REJECT aos perdedores
            for proposal in proposals:
                if proposal.sender != best_truck_msg.sender:
                    msg_reject = Message(to=str(proposal.sender))
                    msg_reject.set_metadata("type", "reject")
                    msg_reject.body = "REJECT - Another truck was selected"
                    await self.send(msg_reject)
                    print( Fore.RED + f"[{self.agent.name}] REJECT sent to {proposal.sender}")
            
            await asyncio.sleep(5)  # Espera antes de avaliar novamente
        
        def select_best(self, proposals_list):
            best_msg = None
            best_score = -999999
            
            for msg in proposals_list:
                lines = msg.body.split('\n')
                score = None
                for line in lines:
                    if line.startswith("Score:"):
                        score = int(float(line.split(":")[1].strip()))
                        break
                
                if score is not None and score > best_score:
                    best_score = score
                    best_msg = msg
            
            if best_msg:
                print(f"[{self.agent.name}] Best score: {best_score} from {best_msg.sender}")
            return best_msg
            

    class ReceiveTruckArrival(CyclicBehaviour):
        """
        Wait for the arrival confirmation from the selected truck.

        Listens for a message from the chosen truck indicating that it has arrived to the bin's location.
        Once the message is received it triggers the transfer phase by adding the behaviour responsible 
        for sending the waste information to the truck.

        Returns:
            None
        """

        async def run(self):
            msg = await self.receive(timeout=120)
            
            if msg:
                print(f"[{self.agent.name}] Truck has arrived!")
                print(f"[{self.agent.name}] Message received with content: {msg.body}")
                self.agent.add_behaviour(self.agent.TransferWasteRequest())


    class TransferWasteRequest(OneShotBehaviour):
        """
        Send the current waste amounts to the truck for pickup.

        Its triggered after the trucl announces its arrival and sends a message containing the quantities of the waste types currently
        stored in the bin. The truck will determine how much waste it can take based on its remaining capaqcity.
        The message uses the metadata type "transferData" and initiates the waste transfer protocol between the bin and the truck.
        Runs once per transfer cycle.

        Returns:
            None
        """

        async def run(self):
            msg = Message(to=self.agent.winning_truck_jid)
            msg.set_metadata("performative", "request")
            msg.set_metadata("type", "transferData")
            msg.body = (
                f"Waste type A: {self.agent.waste_type_a}\n"
                f"Waste type B: {self.agent.waste_type_b}\n"
                f"Waste type C: {self.agent.waste_type_c}\n"
            )
            
            await self.send(msg)
            print(f"[{self.agent.name}] Transfer data sent to truck")
            await asyncio.sleep(1)

    class TransferWasteRespond(CyclicBehaviour):
        """
        Processes the truck's response after waste transfer.

        After the truck determines how much waste it can take, it sends back a message containing the amounts of each waste type left.
        After receiving the information, it updates the bin's internal waste levels and finalizes the transfer cycle.
        It also resets the help-request flags, prints the transfer summary for debugging/monitoring and checks wether the bin still requires assistance, enabling a new cycle.
        Runs once per truck response message.

        Returns:
            None
        """

        async def run(self):

            res = await self.receive(timeout=120)                        # Message received should contain information about overflowing ammount

            if res:
                print(f"[{self.agent.name}] Message received from {res.sender}")
                print(f"[{self.agent.name}] Content: {res.body}")

                # Extract message data
                data = {}
                for line in res.body.splitlines():
                    if ":" in line:
                        key, value = line.split(":", 1)
                        data[key.strip()] = value.strip()

                # Update waste levels
                self.agent.waste_type_a = int(data.get("Left over waste type A", 0))
                self.agent.waste_type_b = int(data.get("Left over waste type B", 0))
                self.agent.waste_type_c = int(data.get("Left over waste type C", 0))

                print(Back.GREEN + f"[{self.agent.name}] Transfer complete!")
                print(f"[{self.agent.name}] Left over ammount: A = {self.agent.waste_type_a}, B = {self.agent.waste_type_b}, C = {self.agent.waste_type_c}")
                
                # Reset flags
                self.agent.is_requesting_help = False
                self.agent.urgent_mode = False
                
                # Verifica se ainda precisa de ajuda
                max_fill = max(
                    self.agent.waste_type_a / self.agent.waste_capacity,
                    self.agent.waste_type_b / self.agent.waste_capacity,
                    self.agent.waste_type_c / self.agent.waste_capacity
                )
                
                if max_fill >= 0.5:  # Se ainda está com +50%, pede ajuda novamente
                    print(Fore.YELLOW + f"[{self.agent.name}] Still needs help, will request again...")
                
                await asyncio.sleep(1)                


    async def setup(self):                      # Required function to setup the agent. 
        """
        Configure the smart bin agent by loading all behaviours and templates.

        This method is automatically executed when the agent starts. It registers every behaviour that the SmartBinAgent requires.
        - Initializes dynamic attributes.
        - Produces waste every simulation tick.
        - Checks fill levels and triggers help requests.
        - Processes truck proposals and selects a winner.
        - Waits for truck arrival confirmation.
        - Sends waste data to the chosen truck.
        - Updates remaining waste after transfer.

        It also defines message templates to ensure that the behaviours react only to messages with specific metadata types
        (arrival, proposal, transferleftovers...). This allows the agent to process multiple interactions in parallel while 
        keeping behaviour logic isolated. 

        This method completes the setup of the agent and prepares it to operate autonomously within the multi-agent environment.
        """

        print(f"Starting Bin Agent {self.name} at {self.initial_location}...")
        
        self.add_behaviour(self.Startup())
        self.add_behaviour(self.GenerateWaste())
        self.add_behaviour(self.MonitorWaste())


        # Template metadata allows methods to wait for spesific msg, exammple:
        # msg.set_metadata("type", "Greetings")
        # The receiver needs a template with metadata matching ("type", "Greetings")
        # If the condition is met, whichever method that is linked to that template will execute



        # Template to continue actions after truck has arrived
        t1 = Template()
        t1.set_metadata("type", "arrival")
        self.add_behaviour(self.ReceiveTruckArrival(), t1)      # Method will execute if a msg has metadata['type'] = 'arrival'

        # Template to do the transfer process
        t2 = Template()
        t2.set_metadata("type", "transferleftovers")
        self.add_behaviour(self.TransferWasteRespond(), t2)

        t3 = Template()
        t3.set_metadata("type", "proposal")
        self.add_behaviour(self.EvaluateProposals(), t3)