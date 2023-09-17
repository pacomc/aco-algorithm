import random
import os
import time
from enum import Enum

# The minimum pheromone in the cell
MINIMUM_PHEROMONE=0.001
MINIMUM_EVAPORATE_PHEROMONE=MINIMUM_PHEROMONE*2
MAXIMUM_PHEROMONE=0.8

class CellType(Enum):
    NORMAL = "NORMAL"
    WALL = "WALL"
    FOOD = "FOOD"
    START = "START"

class Reason(Enum):
    FOOD = "FOOD"

class AntBreed(Enum):
    MINOR = "MINOR"

class Cell:
    '''
    Class to represent a cell in the board
    '''
    def __init__(self, x, y, cell_type=CellType.NORMAL) -> None:
        self.x = x
        self.y = y
        self.pheromone = MINIMUM_EVAPORATE_PHEROMONE
        self.type = cell_type
    
    def set_type(self, type: CellType) -> None:
        self.type = type
    
    def get_type(self) -> CellType:
        return self.type

    def get_pheromone(self) -> float:
        return self.pheromone
    
    def set_pheromone(self, pheromone: float) -> None:
        # Pheromone can not be lower than minimun 
        if MINIMUM_PHEROMONE < pheromone <= MAXIMUM_PHEROMONE:
            self.pheromone = pheromone
        elif pheromone <= MINIMUM_PHEROMONE:
            self.pheromone = MINIMUM_PHEROMONE
        elif pheromone > MAXIMUM_PHEROMONE:
            self.pheromone = MAXIMUM_PHEROMONE

    def get_position(self) -> tuple:
        return (self.x, self.y)
    
    def __repr__(self) -> str:
        return "(" + str(self.x) + ", " + str(self.y) + ", " + str(self.type) + ")"

    def __str__(self) -> str:
        representation = "X"
        if self.type == CellType.NORMAL:
            if self.pheromone < 0.2:
                representation = "░"
            elif 0.2 <= self.pheromone < 0.4:
                representation = "▒"
            elif 0.4 <= self.pheromone < 0.6:
                representation = "▓"
            else:
                representation =  "█"
        elif self.type == CellType.START:
            representation =  "="
        elif self.type == CellType.FOOD:
            representation =  "*"

        return representation
    

class Board:
    '''
    Class to represent the board on which the ants walk
    '''
    def __init__(self, n: int, evaporation_factor:float=0.001) -> None:
        self.cells = [[Cell(x, y) for x in range(n)] for y in range(n)]
        self.n = n
        self.cells[0][0].set_type(CellType.START)
        self.cells[n-1][n-1].set_type(CellType.FOOD)
        self.evaporation_factor = evaporation_factor
    
    def import_from_list(self, list_cell_types: list, evaporation_factor:float=0.001) -> None:
        self.n = len(list_cell_types)
        self.cells = [[Cell(x, y, cell_type=CellType[list_cell_types[x][y]]) for x in range(self.n)] for y in range(self.n)]
        self.evaporation_factor = evaporation_factor

    def set_random_walls(self, wall_probability: float) -> None:
        for cell_row in self.cells:
            for cell in cell_row:
                if cell.get_type() == CellType.NORMAL:
                    cell.set_type(CellType.WALL if random.random() <= wall_probability else CellType.NORMAL)

    def set_evaporation_factor(self, evaporation_factor: float) -> None:
        self.evaporation_factor = evaporation_factor

    def get_cells(self) -> list:
        return self.cells
    
    def get_cell_in_position(self, position: tuple) -> Cell:
        return self.cells[position[1]][position[0]]
            
    def get_neighbour_cells(self, position: tuple, jump:int=1) -> list:
        '''
        Returns a list of neighboring cells
        Jump > 1 can jump walls
        '''
        neighbour_cells = []
        for i in range(-jump, jump+1):
            for j in range(-jump, jump+1):
                # Diagonal is not a neighbour and the same cell is not a neighbour
                if (i != 0 and j != 0) or (i == 0 and j == 0):
                    continue

                new_x = position[0] + i
                new_y = position[1] + j
                
                if 0 <= new_x < self.n and 0 <= new_y < self.n:
                    neighbour_cell = self.cells[new_y][new_x]
                    if not neighbour_cell.get_type() == CellType.WALL:
                        neighbour_cells.append(neighbour_cell)

        return neighbour_cells
    
    def evaporate(self) -> None:
        for cell_row in self.cells:
            for cell in cell_row:
                # Evaporate, but with a value greater than MINIMUM_EVAPORATE_PHEROMONE
                cell.set_pheromone(cell.get_pheromone() - self.evaporation_factor if cell.get_pheromone() - self.evaporation_factor > MINIMUM_EVAPORATE_PHEROMONE else MINIMUM_EVAPORATE_PHEROMONE)

    def export_to_list(self) -> list:
        '''
        Export the board as a list of cell list, but only with string defining its type
        '''
        exported_cells = [list(map(lambda c: c.get_type().value, cell_row)) for cell_row in self.cells]

        return exported_cells

        
    def __str__(self) -> str:
        representation = ""
        for cell_row in self.cells:
            for cell in cell_row:
                representation += str(cell)*2
            representation += "\n"

        return representation[:-1]

class Ant:
    '''
    Class to represent ants 
    '''
    def __init__(self,  pheromone_intensity:float, start_position:tuple=tuple((0, 0)), breed:AntBreed=AntBreed.MINOR, pheromone_loss_factor:float=0.05) -> None:
        self.start_position = start_position
        self.position = start_position
        # Store the path without cycles to return faster and get the path length
        self.position_history_without_cycles = [start_position]
        # Store every step to give less probability the cell already visited and find the food faster
        self.position_history = [start_position]
        self.returning_nest = False
        self.pheromone_intensity = pheromone_intensity
        self.pheromone_loss_factor = pheromone_loss_factor
        self.breed = breed
        self.path_length = None

    def move(self, board: Board) -> None:
        actual_cell = board.get_cell_in_position(self.position)

        # If it is returning to the nest
        if self.returning_nest:
            self.return_nest(board)
        # Return to the nest if finds food
        elif actual_cell.get_type() == CellType.FOOD:
            self.returning_nest = True
            self.path_length = len(self.position_history_without_cycles)
        else:
            neighbour_cells = board.get_neighbour_cells(self.position)
            count_neighbours = len(neighbour_cells)

            if count_neighbours == 0: # There is no neigbour
                print("ANTS ARE TRAPPED!")
            elif count_neighbours == 1 and actual_cell.get_position() != self.start_position: # If ant finds a dead end, it changes the cell type to wall
                actual_cell.set_type(CellType.WALL)
                self.position = neighbour_cells[0].get_position()

            else:
                # More probability if there is pheromone
                # Less probability if the ant has gone by there already
                neighbour_cells_pheromone = [neighbour_cell.get_pheromone() if neighbour_cell.get_position() not in self.position_history else MINIMUM_PHEROMONE for neighbour_cell in neighbour_cells]

                # Choose a weighted random neighbour cell. 
                self.position = random.choices(neighbour_cells, neighbour_cells_pheromone)[0].get_position()

                # To make the ant smarter, it will remember the first time it was in that cell, so it will not cycle
                # list.index(<index>) only returns the first occurrence of <index> in the list
                if self.get_position() in self.position_history:
                    self.position_history = self.position_history[:self.position_history.index(self.get_position()) + 1]
                else:
                    # Store de position in history without cycles
                    self.position_history_without_cycles.append(self.position)

                # Store de position in history
                self.position_history.append(self.position)
    
    def return_nest(self, board: Board, reason:Reason=Reason.FOOD) -> None:
        actual_cell = board.get_cell_in_position(self.position)

        # If the ant has returned home, reset
        if self.position == self.start_position:
            self.start_position = tuple((0, 0))
            self.position = tuple((0, 0))
            self.position_history = [tuple((0, 0))]
            self.position_history_without_cycles = [tuple((0, 0))]
            self.returning_nest = False
            self.path_length = None
        # The ant is returning
        else:
            self.position = self.position_history.pop()

            # On the way back, the pheromone loses intensity, hence the multiplicative factor
            if reason == Reason.FOOD:
                actual_cell.set_pheromone(actual_cell.get_pheromone() + self.pheromone_intensity/self.path_length)


    def get_position(self) -> tuple:
        return self.position

    def __str__(self) -> str:
        representation = "+"
        
        if self.breed == AntBreed.MINOR:
            representation = "·"# + str(self.position)

        return representation

class AntColony:
    '''
    Class to represent the ant colony
    '''
    def __init__(self, length:int,  pheromone_intensity:float) -> None:
        self.length = length
        self.ants = [Ant(pheromone_intensity) for _ in range(self.length)]
    
    def get_ant_positions(self) -> list:
        return [ant.get_position() for ant in self.ants]
    
    def get_ants(self) -> list:
        return self.ants

    def get_ant_in_position(self, position:tuple) -> list:
        return [ant for ant in self.ants if ant.get_position() == position]

    def __str__(self) -> str:
        return "[" + ", ".join(str(ant) for ant in self.ants) + "]"
    

class AntSolver:
    '''
    Class to represent the problem solver
    '''
    def __init__(self, board_size:int=50, ant_size:int=10, evaporation_factor:float=0.001, random_walls:float=0.2) -> None:
        self.evaporation_factor=evaporation_factor
        self.board = Board(board_size, evaporation_factor=evaporation_factor)
        self.board.set_random_walls(random_walls)
        # The intensity will be dividen between all the cell in the shotest path, and the best path will have minimun board_size*2 steps
        pheromone_intensity=board_size*0.7
        self.ant_colony = AntColony(ant_size, pheromone_intensity)
        
    
    def move(self) -> None:
        for ant in self.ant_colony.get_ants():
            ant.move(self.board)
        self.board.evaporate()
    
    def get_board(self) -> Board:
        return self.board

    def set_board(self, board_list) -> None:
        self.board.import_from_list(board_list, evaporation_factor=self.evaporation_factor)

    def __str__(self) -> str:
        representation = ""
        
        cells = self.board.get_cells()
        ant_positions = self.ant_colony.get_ant_positions()

        for cell_row in cells:
            for cell in cell_row:
                cell_position = cell.get_position()
                ant_counts_position = ant_positions.count(cell_position) # How many ants in position
                if ant_counts_position == 0: # No ants in position
                    representation += str(cell)*2
                elif ant_counts_position == 1: # Print breed if in the cell there is just one ant
                    representation += str(self.ant_colony.get_ant_in_position(cell_position)[0]) + " "
                elif ant_counts_position < 10: 
                    representation += str(ant_counts_position) + " " 
                elif 10 <= ant_counts_position < 100:
                    representation += str(ant_counts_position)
                else:
                    representation += "!!"
            representation += "\n"

        return representation[:-1]




if __name__ == '__main__':
    ant_solver = AntSolver(ant_size=20, evaporation_factor=0.006)
    # Here you can set your custom board
    custom_board = [['START', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'WALL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL'], 
                    ['NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL'], 
                    ['NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL'],
                    ['WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL'], 
                    ['WALL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL'], 
                    ['WALL', 'NORMAL', 'WALL', 'WALL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL'], 
                    ['NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL'], 
                    ['NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL'],
                    ['WALL', 'WALL', 'WALL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL'], 
                    ['NORMAL', 'NORMAL', 'WALL', 'WALL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'WALL', 'WALL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL'],
                    ['NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'WALL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL'],
                    ['WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL'], 
                    ['NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL'],
                    ['NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL'],
                    ['NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL'], 
                    ['NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL'], 
                    ['NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL'], 
                    ['NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'WALL', 'NORMAL', 'WALL', 'WALL', 'NORMAL', 'WALL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL'], 
                    ['NORMAL', 'WALL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL'],
                    ['NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'NORMAL', 'WALL', 'NORMAL', 'NORMAL', 'NORMAL', 'FOOD']]
    
    ant_solver.set_board(custom_board)

    # Uncomment this if you want a random board, remember that it may not have a solution
    # ant_solver = AntSolver(ant_size=5, board_size=20, evaporation_factor=0.001)

    # Uncomment this if you want to see the ants moving in real time
    # WARNING: This could be really addictive
    # seconds_watch = 0.1
    # while True:
    #     print(ant_solver)
    #     print()
    #     # print(ant_solver.get_board())
    #     time.sleep(seconds_watch)
    #     os.system('clear')
    #     ant_solver.move()

    # Comment this if you don't want to see the original and the solved board after 1000 rounds
    rounds = 1000
    print(ant_solver)
    for _ in range(rounds):
        ant_solver.move()
    print()
    print(ant_solver.get_board())





