import random
from Classes.Constants import *
from Classes.Materials import Materials
from Classes.TradeOffer import TradeOffer
from Interfaces.AgentInterface import AgentInterface
from Classes.Board import Board
from Classes.DevelopmentCards import *
from Classes.Hand import Hand

class HaoDiego(AgentInterface):
    """
    Interfaz que implementa a un agente
    """

    def __init__(self, agent_id):
        super().__init__(agent_id)
        self.town_number = 0
        self.material_given_more_than_three = None
        self.year_of_plenty_material_one = MaterialConstants.CEREAL
        self.year_of_plenty_material_two = MaterialConstants.MINERAL
        self.hand = Hand()
        self.board = Board()
        self.development_cards_hand = DevelopmentCardsHand()
        self.id = agent_id
        
        # Cada lista dentro del gen contiene los valores entre 0 y 1 de prioridad/posibilidad de usar esa estrategia
        # La suma de todos los valores de una de estas listas dentro del gen debe dar 1 (la suma de todas las posibilidades es igual al 100% de posibilidades)
        self.genes = {
            'begining_priority': [
                0.5,      # MAX_RESOURCES_TYPE
                0.5,      # MAX_DICE_PROB
            ],
            'build_priority': [
                0.2,    #'CITY_FIRST'
                0.2,    #'TOWN_FIRST'
                0.2,    #'ROAD_EXPAND'
                0.2,    #'PORT_HUNTER'
                0.2     #'CARD_SPAM'
            ],  
            'material_priority': [
                0.2,    # clay
                0.2,    # wood
                0.2,    # cereal
                0.2,    # wool
                0.2     # mineral
            ],   
            'thief_priority': [
                0.3,    # MAX_PLAYERS
                0.3,    # MAX_RESOURCES
                0.4     # MAX_DICE_PROB
            ]    
        }
        self.probability_accumulated()
    
    def probability_accumulated(self):
        for key in self.genes:
            accumulated = 0
            for i in range(len(self.genes[key])):
                accumulated += self.genes[key][i]
                self.genes[key][i] = accumulated
                
        return None
    
     
    def choose_priority(self, priority_type):
        """
        Decide qué estrategia seguir según los pesos del cromosoma
        :param priority_type: qué tipo de prioridad se quiere elegir
        :return: int
        """
        prior_list = self.genes[priority_type]
        
        num_rand = random.random()
        for i in range(len(prior_list)):
            if prior_list[i] > num_rand:
                return i
        

    # Los triggers son llamados por el GameDirector las veces que sean necesarias hasta que devuelvan null
    #  o el GameDirector le niegue continuar el trigger
    def on_trade_offer(self, board_instance, offer=TradeOffer(), player_making_offer=int):
        """
        Trigger para cuando llega una oferta. Devuelve si la acepta, la niega o envía una contraoferta
        :param offer: Oferta de comercio que le llega al agente
        :param player_id: ID del jugador
        :param board_instance: Board()
        :return: true, TradeOffer, false
        """
        if offer.gives.has_more(offer.receives):
            return True
        else:
            return False

    def on_turn_start(self):
        """
        Trigger para cuando empieza el turno. Termina cuando hace un return. Se hace antes que tirar dados. Sirve para jugar cartas de desarrollo
        :return: DevelopmentCard, None
        """
        if self.development_cards_hand.hand:
            for i, card in enumerate(self.development_cards_hand.hand):
                if card.type == DevelopmentCardConstants.KNIGHT:
                    return self.development_cards_hand.select_card(i)
        return None

    def on_having_more_than_7_materials_when_thief_is_called(self):
        """
        Trigger que se llama cuando se debe descartar materiales. Si no los descarta el agente, los descartará
        el GameDirector aleatoriamente.
        :return: Hand()
        """
        if self.hand.get_total() > 7:
            for mat in [MaterialConstants.WOOL, MaterialConstants.CEREAL, MaterialConstants.MINERAL, MaterialConstants.CLAY, MaterialConstants.WOOD]:
                if self.hand.get_from_id(mat) > 1:
                    self.hand.remove_material(mat, 1)
                    return self.hand
        return None

    def on_moving_thief(self):
        """
        Trigger para cuando sale un 7 en el dado o se usa una carta de soldado. Esto obliga a mover al ladrón.
        Si no se hace el GameDirector lo hará de manera aleatoria. Incluyendo robar 1 recurso de cualquier
        jugador adyacente a la ficha de terreno seleccionada
        :return: {terrain, player}
        """
        
        terrain_with_thief_id = -1

        for terrain in self.board.terrain:
            if not terrain['has_thief'] and (terrain['probability'] == 6 or terrain['probability'] == 8):
                nodes = self.board.__get_contacting_nodes__(terrain['id'])
                has_own_town = any(self.board.nodes[node_id]['player'] == self.id for node_id in nodes)
                enemy = next((self.board.nodes[node_id]['player'] for node_id in nodes if self.board.nodes[node_id]['player'] != -1), -1)

                if not has_own_town and enemy != -1:
                    return {'terrain': terrain['id'], 'player': enemy}
            elif terrain['has_thief']:
                terrain_with_thief_id = terrain['id']

        return {'terrain': terrain_with_thief_id, 'player': -1}

    def on_turn_end(self):
        """
        Trigger para cuando acaba el turno. Termina cuando hace un return. Sirve para jugar cartas de desarrollo
        :return: DevelopmentCard, None
        """
        development_cards = self.development_cards_hand.hand

        for i, card in enumerate(development_cards):
            if card.type == DevelopmentCardConstants.VICTORY_POINT:
                return self.development_cards_hand.select_card(i)

        return None

    def on_commerce_phase(self):
        """
        Trigger para cuando empieza la fase de comercio. Devuelve una oferta
        :return: TradeOffer, dict{'gives': int, 'receives': int}, None
        """
        if self.hand.resources.has_more(Materials(2, 3, 0, 0, 0)):
            return None

        gives = Materials(0,0,0,0,0)
        receives = Materials(0,0,0,0,0)

        if self.town_number >= 1 and self.hand.resources.has_more(BuildConstants.CITY):
            return None
        elif self.town_number >= 1:
            cereal_hand = self.hand.resources.cereal
            mineral_hand = self.hand.resources.mineral
            wood_hand = self.hand.resources.wood
            clay_hand = self.hand.resources.clay
            wool_hand = self.hand.resources.wool
            total_given_materials = (5 - cereal_hand - mineral_hand - wood_hand - clay_hand - wool_hand)

            if total_given_materials > 0:
                materials_to_give = Materials(0,0,0,0,0)
                for mat, current_amount in {
                    MaterialConstants.CEREAL: cereal_hand,
                    MaterialConstants.MINERAL: mineral_hand,
                    MaterialConstants.WOOD: wood_hand,
                    MaterialConstants.CLAY: clay_hand,
                    MaterialConstants.WOOL: wool_hand,
                }.items():
                    if current_amount > 0:
                        self.hand.remove_material(mat, 1)
                        materials_to_give.add_from_id(MaterialConstants.MINERAL, mat)
                        total_given_materials -= 1
                        if total_given_materials == 0:
                            break

                gives = materials_to_give

        elif self.town_number == 0:
            materials_to_receive = Materials(
                1 - self.hand.resources.cereal,
                0 - self.hand.resources.mineral,
                1 - self.hand.resources.clay,
                1 - self.hand.resources.wood,
                1 - self.hand.resources.wool
            )

            for mat, current_amount in {
                MaterialConstants.CEREAL: self.hand.resources.cereal,
                MaterialConstants.MINERAL: self.hand.resources.mineral,
                MaterialConstants.CLAY: self.hand.resources.clay,
                MaterialConstants.WOOD: self.hand.resources.wood,
                MaterialConstants.WOOL: self.hand.resources.wool,
            }.items():
                if materials_to_receive.get_from_id(mat) < 0 and current_amount > 0:
                    self.hand.remove_material(mat, 1)
                    receives.add_from_id(MaterialConstants.MINERAL, mat)

        trade_offer = TradeOffer(gives, receives)
        return trade_offer

    def on_build_phase(self, board_instance):
        """
        Trigger para cuando empieza la fase de construcción. Devuelve un string indicando qué quiere construir
        :return: dict{'building': str, 'node_id': int, 'road_to': int/None}, None
        """
        
        self.board = board_instance

        def calculate_probability_sum(node_id):
            return sum(self.board.terrain[terrain_piece_id]['probability'] for terrain_piece_id in self.board.nodes[node_id]['contacting_terrain'])

        if self.hand.resources.has_more(BuildConstants.CITY) and self.town_number > 0:
            possibilities = self.board.valid_city_nodes(self.id)
            if possibilities:
                best_node_id = max(possibilities, key=calculate_probability_sum)
                self.town_number -= 1
                return {'building': BuildConstants.CITY, 'node_id': best_node_id}

        if self.hand.resources.has_more(BuildConstants.TOWN):
            possibilities = self.board.valid_town_nodes(self.id)
            if possibilities:
                best_node_id = max(possibilities, key=calculate_probability_sum)
                self.town_number += 1
                return {'building': BuildConstants.TOWN, 'node_id': best_node_id}

        if self.hand.resources.has_more(BuildConstants.ROAD):
            road_possibilities = self.board.valid_road_nodes(self.id)
            if road_possibilities:
                random_road = random.choice(road_possibilities)
                return {'building': BuildConstants.ROAD,
                        'node_id': random_road['starting_node'],
                        'road_to': random_road['finishing_node']}

        if self.hand.resources.has_more(BuildConstants.CARD):
            return {'building': BuildConstants.CARD}

        return None


    def on_game_start(self, board_instance):
        """
        Se llama únicamente al inicio de la partida y sirve para colocar 1 pueblo y una carretera adyacente en el mapa
        :return: int, int
        """
        priority_id = self.choose_priority("begining_priority")
        
        self.board = board_instance
        possibilities = self.board.valid_starting_nodes()
        chosen_node_id = -1
                
        if priority_id == 0: # MAX_RESOURCES_TYPE
            best_terrain = 0
            best_node = 0
            for node_id in possibilities:
                terrain_resources_count = 0
                different_terrains = []
                for terrain_id in self.board.__get_contacting_terrain__(node_id):
                    terrain_type = self.board.__get_terrain_type__(terrain_id)
                    if terrain_type != -1:
                        terrain_resources_count += 1
                        if terrain_type is not different_terrains:
                            different_terrains.append(terrain_type)
                            terrain_resources_count += 1
                if terrain_resources_count > best_terrain:
                    best_terrain = terrain_resources_count
                    best_node = node_id
            chosen_node_id = best_node
            
        elif priority_id == 1: # MAX_DICE_PROB
            best_terrain = 0
            best_node = 0
            for node_id in possibilities:
                terrain_resources_count = 0
                for terrain_id in self.board.__get_contacting_terrain__(node_id):
                    terrain_probability = self.board.__get_probability__(terrain_id)
                    if terrain_probability in [6, 8]:
                        terrain_resources_count += 5
                    elif terrain_probability in [5, 9]:
                        terrain_resources_count += 4
                    elif terrain_probability in [4, 10]:
                        terrain_resources_count += 3
                    elif terrain_probability in [3, 11]:
                        terrain_resources_count += 2
                    elif terrain_probability in [2, 12]:
                        terrain_resources_count += 1
                    
                if terrain_resources_count > best_terrain:
                    best_terrain = terrain_resources_count
                    best_node = node_id
            chosen_node_id = best_node
                
                
        self.town_number += 1
        possible_roads = self.board.nodes[chosen_node_id]['adjacent']
        chosen_road_to_id = random.choice(possible_roads)

        return chosen_node_id, chosen_road_to_id

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
        return self.year_of_plenty_material_one
    
    def on_road_building_card_use(self):
        """
        Se eligen 2 lugares válidos donde construir carreteras. Si no son válidos, el programa pondrá aleatorios
        :return: {'node_id': int, 'road_to': int, 'node_id_2': int, 'road_to_2': int}
        """
        valid_nodes = self.board.valid_road_nodes(self.id)

        if not valid_nodes:
            return None
        
        def calculate_node_score(node):
            return node['probability'] + len(node['adjacent']) - 2 * self.board.count_opponent_towns(node['starting_node'])
        
        valid_nodes.sort(key=calculate_node_score, reverse=True)

        if len(valid_nodes) > 1:
            return {
                'node_id': valid_nodes[0]['starting_node'],
                'road_to': random.choice(valid_nodes[0]['adjacent']),  # Choose a random adjacent node
                'node_id_2': valid_nodes[1]['starting_node'],
                'road_to_2': random.choice(valid_nodes[1]['adjacent'])  # Choose a random adjacent node
            }
        elif len(valid_nodes) == 1:
            return {
                'node_id': valid_nodes[0]['starting_node'],
                'road_to': random.choice(valid_nodes[0]['adjacent']),  # Choose a random adjacent node
                'node_id_2': None,
                'road_to_2': None
            }
        
        return None

    def on_year_of_plenty_card_use(self):
        """
        Se eligen dos materiales (puede elegirse el mismo 2 veces). Te llevas una carta de ese material
        :return: {'material': int, 'material_2': int}
        """
        return {self.year_of_plenty_material_one, self.year_of_plenty_material_two}
