from Classes.Board import Board
from Classes.DevelopmentCards import *
from Classes.Hand import Hand
from Classes.TradeOffer import TradeOffer


class HaoDiego:
    """
    Interfaz que implementa a un agente
    """

    def __init__(self, agent_id):
        self.hand = Hand()
        self.board = Board()
        self.development_cards_hand = DevelopmentCardsHand()
        self.id = agent_id

        self.genes = {
            'build_priority': random.choices(
                ['CITY_FIRST', 'TOWN_FIRST', 'ROAD_EXPAND', 'PORT_HUNTER', 'CARD_SPAM'],
                k=3
            ),  # top 3 estrategias preferidas
            'material_priority': [5, 3, 0, 1, 1],  # clay, wood, cereal, wool, mineral
        }



    # Los triggers son llamados por el GameDirector las veces que sean necesarias hasta que devuelvan null
    #  o el GameDirector le niegue continuar el trigger
    def on_trade_offer(self, board_instance, offer=TradeOffer(), player_id=int):
        """
        Trigger para cuando llega una oferta. Devuelve si la acepta, la niega o envía una contraoferta
        :param offer: Oferta de comercio que le llega al agente
        :param player_id: ID del jugador
        :param board_instance: Board()
        :return: true, TradeOffer, false
        """
        return False
    
    def on_turn_start(self):
        """
        Trigger para cuando empieza el turno. Termina cuando hace un return. Se hace antes que tirar dados. Sirve para jugar cartas de desarrollo
        :return: DevelopmentCard, None
        """
        return None

    def on_having_more_than_7_materials_when_thief_is_called(self):
        """
        Trigger que se llama cuando se debe descartar materiales. Si no los descarta el agente, los descartará
        el GameDirector aleatoriamente.
        :return: Hand()
        """
        return self.hand

    def on_moving_thief(self):
        """
        Trigger para cuando sale un 7 en el dado o se usa una carta de soldado. Esto obliga a mover al ladrón.
        Si no se hace el GameDirector lo hará de manera aleatoria. Incluyendo robar 1 recurso de cualquier
        jugador adyacente a la ficha de terreno seleccionada
        :return: {terrain, player}
        """
        terrain_with_thief_id = -1
        best_target = None
        max_enemy_towns = 0

        for terrain in self.board.terrain:
            if terrain['has_thief']:
                terrain_with_thief_id = terrain['id']
                continue

            nodes = self.board.__get_contacting_nodes__(terrain['id'])
            if not nodes:
                continue

            enemy_players = set()
            has_own_town = False

            for node_id in nodes:
                player = self.board.nodes[node_id]['player']
                if player == self.id:
                    has_own_town = True
                    break
                elif player != -1:
                    enemy_players.add(player)

            if not has_own_town and enemy_players:
                # Preferir el terreno con más pueblos enemigos
                if len(enemy_players) > max_enemy_towns:
                    max_enemy_towns = len(enemy_players)
                    best_target = {'terrain': terrain['id'], 'player': enemy_players.pop()}

        if best_target:
            return best_target

        return {'terrain': terrain_with_thief_id, 'player': -1}


    def on_turn_end(self):
        """
        Trigger para cuando acaba el turno. Termina cuando hace un return. Sirve para jugar cartas de desarrollo
        :return: DevelopmentCard, None
        """
        return None

    def on_commerce_phase(self):
        """
        Trigger para cuando empieza la fase de comercio. Devuelve una oferta
        :return: TradeOffer, dict{'gives': int, 'receives': int}, None
        """
        max_total = 13
        current_total = self.hand.get_total()
        if current_total >= max_total:
            return None # no comerciamos para no sobrepasar nuestro limite impuesto

        offer = TradeOffer()
        material_priority = self.genes['material_priority']

        # Intentar generar una oferta útil y válida
        for give_index, give_mat in enumerate(material_priority[::-1]):  # menos prioritarios
            give_amount = self.hand.get_from_id(give_mat)
            if give_amount < 2:
                continue  # necesitas al menos 2 para ofrecer algo decente

            for get_index, get_mat in enumerate(material_priority):  # más prioritarios
                if give_mat == get_mat:
                    continue

                # Si el material que queremos tiene más prioridad (índice menor)
                if get_index < (len(material_priority) - give_index):
                    ratio = 2  # ratio de intercambio (puede ser 2:1, 3:1, etc.)
                    if give_amount >= ratio and current_total - ratio + 1 <= max_total:
                        offer.set_offer(give={give_mat: ratio}, receive={get_mat: 1})
                        return offer

        return None  # si no se cumple ninguna condición


    def on_build_phase(self, board_instance):
        """
        Elige una acción de construcción basada en prioridades del cromosoma.
        """
        self.board = board_instance
        best_score = -1
        best_action = None

        for strategy in self.genes['build_priority']:
            score, action = self.evaluate_strategy(strategy)
            if score > best_score and action:
                best_score = score
                best_action = action

        return best_action

    def evaluate_strategy(self, strategy):
        score = 0
        action = None

        if strategy == 'CITY_FIRST':
            if self.hand.resources.has_more(BuildConstants.CITY) and self.town_number > 0:
                candidates = self.board.valid_city_nodes(self.id)
                for node_id in candidates:
                    s = sum(self.board.terrain[tid]['probability']
                            for tid in self.board.nodes[node_id]['contacting_terrain']
                            if tid in self.board.terrain)
                    if s > score:
                        score = s + 10
                        action = {'building': BuildConstants.CITY, 'node_id': node_id, 'road_to': None}

        elif strategy == 'TOWN_FIRST':
            if self.hand.resources.has_more(BuildConstants.TOWN):
                candidates = self.board.valid_town_nodes(self.id)
                for node_id in candidates:
                    s = sum(self.board.terrain[tid]['probability']
                            for tid in self.board.nodes[node_id]['contacting_terrain']
                            if tid in self.board.terrain)
                    if s > score:
                        score = s + 5
                        action = {'building': BuildConstants.TOWN, 'node_id': node_id, 'road_to': None}

        elif strategy == 'ROAD_EXPAND':
            if self.hand.resources.has_more(BuildConstants.ROAD):
                road_nodes = self.board.valid_road_nodes(self.id)
                for road_obj in road_nodes:
                    fin = road_obj['finishing_node']
                    if self.board.nodes[fin]['player'] == -1:
                        future = [n for n in self.board.nodes[fin]['adjacent']
                                if self.board.nodes[n]['player'] == -1]
                        s = len(future)
                        if s > score:
                            score = s * 2
                            action = {'building': BuildConstants.ROAD,
                                    'node_id': road_obj['starting_node'],
                                    'road_to': fin}

        elif strategy == 'PORT_HUNTER':
            if self.hand.resources.has_more(BuildConstants.ROAD):
                road_nodes = self.board.valid_road_nodes(self.id)
                for road_obj in road_nodes:
                    fin = road_obj['finishing_node']
                    if self.board.is_coastal_node(fin) and self.board.nodes[fin]['harbor'] != HarborConstants.NONE:
                        score = 12
                        action = {'building': BuildConstants.ROAD,
                                'node_id': road_obj['starting_node'],
                                'road_to': fin}

        elif strategy == 'CARD_SPAM':
            if self.hand.resources.has_more(BuildConstants.CARD):
                score = 4
                action = {'building': BuildConstants.CARD, 'node_id': None, 'road_to': None}

        return score, action



    def calculate_fitness(self, node_id):
        """
        Calcula la puntuación de un nodo basado en producción y variedad.
        """
        if node_id not in self.board.nodes:
            return 0

        score = 0
        resource_types = set()

        # Usamos los terrenos que están en contacto con el nodo
        contacting_terrain = self.board.nodes[node_id].get('contacting_terrain', [])

        for terrain_id in contacting_terrain:
            terrain_data = self.board.terrain.get(terrain_id, {})

            number = terrain_data.get('number')
            if number is None:
                continue

            # Valor por número del dado
            if number in [6, 8]:
                score += 5
            elif number in [5, 9]:
                score += 4
            elif number in [4, 10]:
                score += 3
            elif number in [3, 11]:
                score += 2
            elif number in [2, 12]:
                score += 1

            # Penalización por desierto, bonificación por diversidad
            terrain_type = terrain_data.get('terrain')
            if terrain_type == 'desert':
                score -= 2
            elif terrain_type is not None:
                resource_types.add(terrain_type)

        # Bonus por diversidad de recursos
        score += len(resource_types) * 2

        return score

    def on_game_start(self, board_instance):
        """
        Se llama únicamente al inicio de la partida y sirve para colocar 1 pueblo y una carretera adyacente en el mapa
        :return: int, int
        """
        self.board = board_instance
        population = self.board.valid_starting_nodes()

        # Parámetros del algoritmo genético
        population_size = len(population)
        generations = 10
        mutation_rate = 0.1

        # Población inicial (nodos aleatorios)
        current_population = random.sample(population, min(population_size, 10))

        for _ in range(generations):
            # Evaluar fitness
            scored = [(node_id, self.calculate_fitness(node_id)) for node_id in current_population]
            scored.sort(key=lambda x: x[1], reverse=True)

            # Seleccionar los 50% mejores
            survivors = [node_id for node_id, _ in scored[:len(scored) // 2]]

            # Reproducir con mutaciones
            new_generation = survivors[:]
            while len(new_generation) < len(current_population):
                parent = random.choice(survivors)
                if random.random() < mutation_rate:
                    # Mutar el nodo con uno aleatorio distinto
                    mutation = random.choice([n for n in population if n != parent])
                    new_generation.append(mutation)
                else:
                    new_generation.append(parent)  # sin cambio

            current_population = new_generation

        # Elegir el mejor nodo final
        best_node = max(current_population, key=lambda nid: self.calculate_fitness(nid))

        # Elegir carretera aleatoria adyacente
        road_options = self.board.nodes[best_node]['adjacent']
        best_road_to = random.choice(road_options)

        return best_node, best_road_to

    def on_monopoly_card_use(self):
        """
        Se elige un material. El resto de jugadores te entregan dicho material
        0: Cereal
        1: Mineral
        2: Clay
        3: Wood
        4: Wool
        :return: int, representa el material elegido
        """
        return None

    def on_road_building_card_use(self):
        """
        Se eligen 2 lugares válidos donde construir carreteras. Si no son válidos, el programa pondrá aleatorios
        :return: {'node_id': int, 'road_to': int, 'node_id_2': int, 'road_to_2': int}
        """
        return None

    def on_year_of_plenty_card_use(self):
        """
        Se eligen dos materiales (puede elegirse el mismo 2 veces). Te llevas una carta de ese material
        :return: {'material': int, 'material_2': int}
        """
        return None
