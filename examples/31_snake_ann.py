"""
"""
import random

from PySide2 import QtCore

from PySide2.QtCore import QRect
from PySide2.QtCore import QSize
from PySide2.QtCore import QTimer
from PySide2.QtGui import QPainter
from PySide2.QtWidgets import QWidget, QApplication

from sfwidgets.neuralnetwork import Network, NetworkPainter
from sfwidgets.snake import SnakeGame
MUTATION_RATE = 0.01

def make_snake_network(snake):
    n = Network(snake.grid.height * snake.grid.width,
                [7, 7, 7], 5)
    return n


class SnakeDNA(object):
    def __init__(self, value):
        self.value = value

    def crossover(self, dna):
        if False:
            midpoint = len(self.value) / 2
            midpoint = int(midpoint)
            part_a = self.value[:midpoint]
            part_b = dna.value[midpoint:]
            value = part_a + part_b

        else:
            average_list = []
            for i, v in enumerate(self.value):
                average_list.append((v + dna.value[i]) / 2.0)
            value = average_list
        dna = SnakeDNA(value)
        dna.fitness = 0
        return dna

    def mutate(self, mutation_rate):
        new_value = []
        for v in self.value:
            if random.random() < mutation_rate:
                v = -1 + random.random() * 2
                new_value.append(v)
            else:
                new_value.append(v)

        self.value = new_value



class SnakePhenotype(object):
    """snake phenotype
    """

    @staticmethod
    def apply_network_decision(network, snake):
        outputs = [n.output for n in network.output_layer]
        strongest_index = outputs.index(max(outputs))
        if snake.game_over:
            return

        if strongest_index == 0:
            snake.key_pressed(QtCore.Qt.Key_Left)
        if strongest_index == 1:
            snake.key_pressed(QtCore.Qt.Key_Up)
        if strongest_index == 2:
            snake.key_pressed(QtCore.Qt.Key_Right)
        if strongest_index == 3:
            snake.key_pressed(QtCore.Qt.Key_Down)
        if strongest_index == 4:
            pass

    @staticmethod
    def get_network_response(snake):
        inputs = []
        for y in range(snake.grid.height):
            for x in range(snake.grid.width):
                value = 0.0
                if snake.snake.x == x and snake.snake.y == y:
                    value = 1.0
                for body in snake.bodies:
                    if body.x == x and body.y == y:
                        value = 0.5
                if snake.food.x == x and snake.food.y == y:
                    value = -1.0

                inputs.append(value)

        return inputs

    def __init__(self, dna):
        self.dna = dna
        self.snake = SnakeGame()
        self.network = make_snake_network(self.snake)
        self.network.setup()
        self.network.import_weights(dna.value)
        self.is_finished = False
        self.last_score = 0
        self.fitness = 0
        self.score_check_max_ticks = 20
        self.score_check_ticks = 0

    def get_network_inputs(self):
        inputs = []
        for y in self.snake.grid.height:
            for x in self.snake.grid.width:
                value = 0.0
                if self.snake.snake.x == x and self.snake.snake.y == y:
                    value = 1.0
                for body in self.snake.bodies:
                    if body.x == x and body.y == y:
                        value = 0.5
                if self.snake.food.x == x and self.snake.food.y == y:
                    value = -1.0

                inputs.append(value)

        return inputs

    def tick(self):
        self.snake.tick()
        response = SnakePhenotype.get_network_response(self.snake)
        self.network.respond(response)
        SnakePhenotype.apply_network_decision(self.network, self.snake)
        self.is_finished = self.snake.game_over

        self.score_check_ticks += 1
        if self.score_check_ticks > self.score_check_max_ticks:
            self.score_check_ticks = 0
            if self.last_score == self.snake.score:
                self.is_finished = True
            else:
                self.last_score = self.snake.score

        self.fitness += 1


class SnakeGenetic(object):
    START = 'start'
    CREATE_PHENOTYPES = 'create_phenotypes'
    TICK_PHENOTYPES = 'tick_phenotypes'
    CROSSOVER = 'crossover'
    MUTATE = 'mutate'
    STORE_BEST_PHENOTYPE = 'store best phenotype'

    def __init__(self):
        self.generation = 0
        self.total_population = 40
        self.population = []
        self.phenotypes = []
        self.state = self.START
        self.best_phenotype = None
        self.generation_incremented_func = None

    def create_penhotypes(self):
        self.phenotypes = []
        for dna in self.population:
            phenotype = SnakePhenotype(dna)
            self.phenotypes.append(phenotype)

    def get_best_phenotype(self):
        return self.best_phenotype

    def setup(self):
        self.population = []

        # setup
        for i in range(self.total_population):
            n = make_snake_network(SnakeGame())
            n.setup()

            dna = SnakeDNA(n.export_weights())
            self.population.append(dna)

    def tick_phenotypes(self):
        for phenotype in self.phenotypes:
            phenotype.tick()

    def crossover(self):
        total_fitness = sum([p.fitness for p in self.phenotypes])

        def pick_pheno_type():
            target = random.random()
            count = 0.0

            for pheno_type in self.phenotypes:
                if pheno_type.fitness == 0:
                    continue

                fitness_normal = float(pheno_type.fitness) / float(
                    total_fitness)

                if target <= count + fitness_normal:
                    return pheno_type

                count += fitness_normal

        # generate the new population
        population = []
        for i in range(self.total_population):
            phenotype_a = pick_pheno_type()
            phenotype_b = pick_pheno_type()
            new_dna = phenotype_a.dna.crossover(phenotype_b.dna)
            population.append(new_dna)

        self.population = population
        self.generation += 1

        if self.generation_incremented_func:
            self.generation_incremented_func()

    def store_best_phenotype(self):
        fitness_list = [p.fitness for p in self.phenotypes]
        self.best_phenotype = self.phenotypes[fitness_list.index(max(fitness_list))]

    def mutate(self):
        for dna in self.population:
            dna.mutate(MUTATION_RATE)

    def tick(self):
        if self.state == self.START:
            self.state = self.CREATE_PHENOTYPES
        elif self.state == self.CREATE_PHENOTYPES:
            self.create_penhotypes()
            self.state = self.TICK_PHENOTYPES
        elif self.state == self.TICK_PHENOTYPES:
            self.tick_phenotypes()
            if all([n.is_finished for n in self.phenotypes]):
                self.state = self.STORE_BEST_PHENOTYPE
        elif self.state == self.STORE_BEST_PHENOTYPE:
            self.store_best_phenotype()
            self.state = self.CROSSOVER
        elif self.state == self.CROSSOVER:
            self.crossover()
            self.state = self.MUTATE
        elif self.state == self.MUTATE:
            self.mutate()
            self.state = self.CREATE_PHENOTYPES


class SnakeWidget(QWidget):
    def __init__(self):
        super(SnakeWidget, self).__init__()
        self.snake = SnakeGame()
        self.setCursor(QtCore.Qt.BlankCursor)

        self.snakegenetic = SnakeGenetic()
        self.snakegenetic.setup()
        self.snakegenetic.generation_incremented_func = self.generation_incremented

        self.network = make_snake_network(self.snake)
        self.network.setup()
        self.network_painter = NetworkPainter(self.network)

        self.tick_timer = QTimer()
        self.tick_timer.timeout.connect(self.tick)
        self.tick_timer.setInterval(20)
        self.tick_timer.start()

    def tick(self):
        self.snakegenetic.tick()
        self.snake.tick()
        response = SnakePhenotype.get_network_response(self.snake)
        self.network.respond(response)
        SnakePhenotype.apply_network_decision(self.network, self.snake)

        self.update()

    def showEvent(self, event):
        r = QRect(0, 0, self.width() / 2, self.height() / 2)
        self.network_painter.rect = r
        self.snake.rect = self.rect()
        self.snake.width = self.width()
        self.snake.height = self.height()
        self.update()

    def sizeHint(self):
        return QSize(300, 300)

    def paintEvent(self, event):
        painter = QPainter(self)
        self.snake.paint(painter)
        self.network_painter.paint(painter)
        painter.drawText(170, 20, 'state: {}'.format(self.snakegenetic.state))
        painter.drawText(170, 40, 'generation: {}'.format(self.snakegenetic.generation))

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space:
            dna = self.snakegenetic.get_best_phenotype().dna
            self.network.import_weights(dna.value)
            self.snake.reset()

    def generation_incremented(self):
        dna = self.snakegenetic.get_best_phenotype().dna
        self.network.import_weights(dna.value)
        self.snake.reset()


def main():
    app = QApplication([])
    w = SnakeWidget()
    w.show()
    app.exec_()


if __name__ == '__main__':
    main()
