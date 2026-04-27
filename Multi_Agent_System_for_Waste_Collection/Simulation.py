# ficheiro simulation

"""
Simulation setup for the multi-agent waste management system.

Initializes SmartBinAgent, TruckAgent and RecyclingCenterAgent. Assigns their starting positions, starts all agents and runs the continuous simulation
responsible for visualizing the grid and mantaining the system alive.
"""
import spade
import asyncio
from SmartBinAgent import SmartBinAgent
from TruckAgent import TruckAgent
from RecyclingCenterAgent import RecyclingCenterAgent
from VisualizationHelper import VisualizationHelper
import random

import random
import math

def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def generate_positions(grid_size, n_bins, n_centers, min_dist_all=3, max_attempts=2000, seed=None):
    """
    Gera posições únicas para n_centers e n_bins numa grelha grid_size x grid_size garantindo:
      - distância Manhattan >= min_dist_all entre quaisquer pares bin↔bin e bin↔center;
      - distância Manhattan >= min_dist_centers entre quaisquer pares center↔center,
        onde min_dist_centers = ceil(3/5 * grid_size).

    Args:
        grid_size (int): tamanho da grelha (grid_size x grid_size).
        n_bins (int): número de bins a gerar.
        n_centers (int): número de centers a gerar.
        min_dist_all (int): distância mínima para pares que envolvem bins.
        max_attempts (int): número máximo de embaralhamentos/tentativas.
        seed (int|None): seed para reproducibilidade.

    Retorna:
        (centers_list, bins_list)

    Lança RuntimeError se não for possível encontrar configuração válida dentro de max_attempts.
    """
    if seed is not None:
        random.seed(seed)

    if n_bins + n_centers > grid_size * grid_size:
        raise ValueError("Mais agentes do que células no grid")

    # distância mínima exigida entre centers
    min_dist_centers = math.ceil((3/5) * grid_size)
    all_cells = [(x, y) for x in range(grid_size) for y in range(grid_size)]

    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        random.shuffle(all_cells)
        centers = []
        bins = []
        used = set()

        # Preencher centers garantindo distância mínima entre centers
        for cell in all_cells:
            if len(centers) >= n_centers:
                break
            if cell in used:
                continue
            if all(manhattan(cell, c) >= min_dist_centers for c in centers):
                centers.append(cell)
                used.add(cell)

        if len(centers) < n_centers:
            continue  # nova tentativa

        # Agora preencher bins garantindo:
        # - distância >= min_dist_all para todos os centers
        # - distância >= min_dist_all entre bins
        for cell in all_cells:
            if len(bins) >= n_bins:
                break
            if cell in used:
                continue
            if all(manhattan(cell, c) >= min_dist_all for c in centers) and all(manhattan(cell, b) >= min_dist_all for b in bins):
                bins.append(cell)
                used.add(cell)

        if len(bins) < n_bins:
            continue  # nova tentativa

        # sucesso
        return centers, bins

    raise RuntimeError(
        f"Não foi possível gerar posições após {max_attempts} tentativas. "
        f"Tente aumentar grid_size, reduzir N_bins/N_centers, diminuir min_dist_all ou reduzir a fração 3/5."
    )




async def main():
    """
    Starts the multi-agent waste management simulation.

    Creates and launches all agents required for the system:
        - SmartBinAgents
        - TruckAgentys
        - RecyclingCenterAgents
    
    The function initializes agent instances with their positions and parameters, starts all agents, runs the simulation loop responsible for grid visualization
    and handles graceful shutdown when interrupted.
    """

    grid_size = int(input("Size of the simulation = "))
    N_agents = grid_size // 3

    # user inputs
    N_bins_input = int(input("Number of bins = "))
    N_trucks = int(input("Number of trucks = "))
    N_centers_input = int(input("Number of recycling centers = "))

    # regras de distância
    min_dist_all = 3
    D_centers = (3 * grid_size + 4) // 5  # ceil(3/5 * grid_size) sem usar float
    # cálculo do "raio" de Manhattan r = floor((D-1)/2)
    r_centers = (D_centers - 1) // 2
    r_bins = (min_dist_all - 1) // 2

    # tamanho da "bola" de Manhattan de raio r: A(r) = 1 + 2*r*(r+1)
    A_centers = 1 + 2 * r_centers * (r_centers + 1)
    A_bins = 1 + 2 * r_bins * (r_bins + 1)

    L2 = grid_size * grid_size

    # máximo conservador de centers que a grelha pode suportar
    max_centers = max(1, L2 // A_centers)

    # limita centers ao máximo permitido e também pelo desejo mínimo baseado em N_agents
    N_centers = N_centers_input
    if N_centers < N_agents:
        N_centers = N_agents
    if N_centers > max_centers:
        N_centers = max_centers

    # reserva area conservadora para afastar bins dos centers (usando A_bins)
    reserved_by_centers = N_centers * A_bins
    remaining_cells = max(0, L2 - reserved_by_centers)

    # máximo conservador de bins após reservar espaço dos centers
    max_bins_after_centers = max(0, remaining_cells // A_bins)

    # ajustar N_bins para não violar restrições (usar o input do utilizador, mas limitar)
    N_bins = N_bins_input
    if N_bins > max_bins_after_centers:
        N_bins = max_bins_after_centers

    # fallback para garantir pelo menos 1 bin/center caso a grelha seja pequena
    if N_centers < 1:
        N_centers = 1
    if N_bins < 1:
        N_bins = 1


    center_locations, bin_locations = generate_positions(grid_size, n_bins=N_bins, n_centers=N_centers, seed=42)

    print("=" * 60)
    print(" 🚛 SMART WASTE MANAGEMENT SYSTEM 🗑")
    print("=" * 60)
    print("\nInitializing agents...\n")

    # --------------- Start Smart Bin Agent ------------------------
    bin_dict = {}
    for i in range(N_bins):
        bin_dict[f"SBA{i}"] = SmartBinAgent(f"SBA{i}@localhost", "password", initial_location=bin_locations[i], grid_center=grid_size//2)
        await bin_dict[f"SBA{i}"].start(auto_register=True)
        print(f"✓ Smart Bin Agent {i} started at {bin_locations[i]}")

    # ----------------- Start Truck Agents -------------------------
    truck_dict = {}
    
    for i in range(N_trucks):
        truck_dict[f"TA{i}"] = TruckAgent(f"TA{i}@localhost", "password", initial_location=center_locations[i % len(center_locations)])
        await truck_dict[f"TA{i}"].start(auto_register=True)
        print(f"✓ Truck Agent {i} started at {center_locations[i % len(center_locations)]}")


    # --------------- Start Recycling Center Agents -----------------
    center_dict = {}
    
    for i in range(N_centers):
        center_dict[f"RCA{i}"] = RecyclingCenterAgent(f"RCA{i}@localhost", "password", initial_location=center_locations[i])
        await center_dict[f"RCA{i}"].start(auto_register=True)
        print(f"✓ Recycling Center Agent {i} started at {center_locations[i]}")


    print("\n" + "=" * 60)
    print("🚀 Simulation running... (Press Ctrl+C to stop)")
    print("=" * 60)


    # --- loop de visualização (substitui o sleep único) ---
    try:
        while True:
            # construir dicts com as posições atuais (uso de getattr para fallback)
            truck_positions = {}
            for name, agent in truck_dict.items():
                pos = getattr(agent, "location", None)
                if pos is None and hasattr(agent, "initial_location"):
                    pos = agent.initial_location
                if pos is not None:
                    truck_positions[name] = pos

            bin_positions = {}
            for name, agent in bin_dict.items():
                pos = getattr(agent, "location", None)
                if pos is None and hasattr(agent, "initial_location"):
                    pos = agent.initial_location
                if pos is not None:
                    bin_positions[name] = pos

            rc_positions = {}
            for name, agent in center_dict.items():
                pos = getattr(agent, "location", None)
                if pos is None and hasattr(agent, "initial_location"):
                    pos = agent.initial_location
                if pos is not None:
                    rc_positions[name] = pos

            VisualizationHelper.draw_grid(
                truck_positions=truck_positions,
                bin_positions=bin_positions,
                rc_positions=rc_positions,
                grid_size=grid_size
            )

            await asyncio.sleep(5)   # taxa de frame; ajusta entre 0.2 e 2s conforme necessidade
    except KeyboardInterrupt:
        print("\n\n⚠️  Simulation interrupted by user")


    print("\n" + "=" * 60)
    print("🛑 Stopping all agents...")
    print("=" * 60)

    # Stop all agents
    for bin in bin_dict.values():
        await bin.stop()
    for truck in truck_dict.values():
        await truck.stop()
    for center in center_dict.values():
        await center.stop()

    print("✓ All agents stopped successfully")
    print("\n👋 Goodbye!\n")


if __name__ == "__main__":
    spade.run(main())



