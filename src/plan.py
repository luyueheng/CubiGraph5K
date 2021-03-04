# Author: Yueheng Lu <luyueheng.arch@gmail.com>

# Imports
from typing import List, Tuple, Dict
from shapely.geometry import Polygon
from bs4 import BeautifulSoup
from bs4.element import Tag as bs4Tag
from collections import defaultdict
from queue import Queue


room_colors = {
    # map from class name (after Space)
    'Bedroom':'deepskyblue',
    'LivingRoom':'crimson',
    'Kitchen':'gold',
    'Dining':'gold',
    'Bath':'aquamarine',
    'Entry':'hotpink',
    'Storage':'olivedrab',
    'Outdoor':'lawngreen',
    # color to white for ones you want to ignore
    'Other': 'hotpink'
}

room_name_map = {
    "Alcove": "LivingRoom",
    "Attic": "Other",
    "Ballroom": "LivingRoom",
    "Bar": "Dining",
    "Basement": "Storage",
    "Bath": "Bath",
    "Bedroom": "Bedroom",
    "Below150cm": "LivingRoom",
    "CarPort": "Garage",
    "Church": "Bedroom",
    "Closet": "Storage",
    "ConferenceRoom": "LivingRoom",
    "Conservatory": "Bedroom",
    "Counter": "Dining",
    "Den": "Bedroom",
    "Dining": "Dining",
    "DraughtLobby": "Entry",
    "DressingRoom": "Storage",
    "EatingArea": "Dining",
    "Elevated": "LivingRoom",
    "Elevator": "LivingRoom",
    "Entry": "Entry",
    "ExerciseRoom": "LivingRoom",
    "Garage": "Garage",
    "Garbage": "Storage",
    "Hall": "LivingRoom",
    "HallWay": "Entry",
    "HotTub": "Bath",
    "Kitchen": "Kitchen",
    "Library": "Bedroom",
    "LivingRoom": "LivingRoom",
    "Loft": "LivingRoom",
    "Lounge": "LivingRoom",
    "MediaRoom": "LivingRoom",
    "MeetingRoom": "LivingRoom",
    "Museum": "LivingRoom",
    "Nook": "Bedroom",
    "Office": "LivingRoom",
    "OpenToBelow": "LivingRoom",
    "Outdoor": "Outdoor",
    "Pantry": "Kitchen",
    "Reception": "LivingRoom",
    "RecreationRoom": "LivingRoom",
    "RetailSpace": "LivingRoom",
    "Room": "Other",
    "Sanctuary": "Bedroom",
    "Sauna": "Bath",
    "ServiceRoom": "Storage",
    "ServingArea": "Storage",
    "Skylights": "Other",
    "Stable": "Outdoor",
    "Stage": "LivingRoom",
    "StairWell": "LivingRoom",
    "Storage": "Storage",
    "SunRoom": "Bedroom",
    "SwimmingPool": "LivingRoom",
    "TechnicalRoom": "Storage",
    "Theatre": "LivingRoom",
    "Undefined": "Other",
    "UserDefined": "Other",
    "Utility": "Storage",
    "Background": "Background"
}

room_type = ['LivingRoom', 'Bedroom', 'Kitchen', 'Dining', 'Bath', 'Storage', 'Entry', 'Garage', 'Other', 'Outdoor']


def get_points_from_svg_group(svg_group: bs4Tag) -> List[Tuple[float, float]]:
    points_str = svg_group.find('polygon').attrs['points'] 
    return [(float(p.split(',')[0]), float(p.split(',')[1])) for p in points_str.strip().split(' ')]


def mean(nums: List[float]) -> float:
    return sum(nums) / len(nums)


class Tag:

    def __init__(self, name: str, attrs: Dict):
        self.name = name
        self.attrs = attrs
        self.children = []
    
    def add(self, tag: 'Tag') -> None:
        self.children.append(tag)

    def __str__(self) -> str:
        return '<{} {}>\n{}</{}>\n'.format(
            self.name,
            ' '.join(['{}="{}"'.format(k, v) for k, v in self.attrs.items()]),
            ''.join([str(c) for c in self.children]),
            self.name)


class Room:

    def __init__(self, svg_space_group: bs4Tag, room_type_count: Dict):
        self.points = get_points_from_svg_group(svg_space_group)
        self.type = room_name_map[svg_space_group.attrs['class'][1]]
        self.name = '{}_{}'.format(self.type, room_type_count[self.type]+1)
        room_type_count[self.type] += 1
        self.center_point = self._get_center_point()
        self.adjacent_doors = set() # generate by calling self.get_adjacent_doors()

    def _get_center_point(self) -> Tuple[float, float]:
        return (mean([p[0] for p in self.points]), mean([p[1] for p in self.points]))

    def to_svg_polygon(self) -> 'Tag':
        plg_attrs = {'fill' : 'none', 'stroke-width' : 5}
        plg_attrs['points'] = ' '.join(['{},{}'.format(p[0], p[1]) for p in self.points])
        plg_attrs['stroke'] = room_colors.get(self.type, 'grey')
        return Tag('polygon', plg_attrs)
    
    def to_shapely_polygon(self) -> Polygon:
        return Polygon(self.points)
    
    def get_adjacent_doors(self, doors: List['Door']) -> None:
        room = self.to_shapely_polygon()
        for d in doors:
            if room.intersection(d.to_shapely_polygon().buffer(1.0)).area > 10.0:
                self.adjacent_doors.add(d.name)


class Door:

    def __init__(self, svg_space_group: bs4Tag, idx: int):
        self.points = get_points_from_svg_group(svg_space_group)
        self.name = 'Door_{}'.format(idx + 1)
        
    def to_svg_polygon(self) -> 'Tag':
        plg_attrs = {'fill' : 'none','stroke' : 'black', 'stroke-width' : 5}
        plg_attrs['points'] = ' '.join(['{},{}'.format(p[0], p[1]) for p in self.points])
        return Tag('polygon', plg_attrs)

    def to_shapely_polygon(self) -> Polygon:
        return Polygon(self.points)


class Plan:

    def __init__(self, svg: bs4Tag):
        self.rooms = [] # parse from svg
        self.name2room = {}
        self.name2index = {}
        self.doors = [] # parse from svg
        self.name2door = {}
        self.relation = [] # generate by calling self.generate_room_relation()
        self.room_type_count = defaultdict(int)
        self.door_count = 0
        self.svg_dimension = (svg.attrs['height'], svg.attrs['width'])

        for r in svg.find_all('g', attrs={'class': 'Space'}):
            room = Room(r, self.room_type_count)
            self.rooms.append(room)
            self.name2room[room.name] = room
        
        self.room_names = self.name2room.keys()

        for d in svg.find_all('g', attrs={'class': 'Threshold'}):
            door = Door(d, self.door_count)
            self.doors.append(door)
            self.door_count += 1
            self.name2door[door.name] = door
        
        self.name2index = {name : i for i, name in enumerate(self.name2room)}

    def generate_room_relation(self) -> None:
        for room in self.rooms:
            room.get_adjacent_doors(self.doors)
        
        for i in range(len(self.rooms)):
            for j in range(i+1, len(self.rooms)):
                room1 = self.rooms[i]
                room2 = self.rooms[j]
                if room1.to_shapely_polygon().buffer(1.0).intersection(room2.to_shapely_polygon().buffer(1.0)).area > 5.0:
                    self.relation.append((room1.name, 1, room2.name))
                elif room1.adjacent_doors.intersection(room2.adjacent_doors):
                    self.relation.append((room1.name, 2, room2.name))
                else:
                    self.relation.append((room1.name, 0, room2.name))

    def get_adjacency_list(self) -> dict:
        relation_adj_list = {name : {} for name in self.name2room}
        for name1, label, name2 in self.relation:
            if label != 0:
                relation_adj_list[name1][name2] = label
                relation_adj_list[name2][name1] = label
        return relation_adj_list

    def get_adjacency_matrix(self) -> list:
        relation_adj_matrix = [[0 for name in self.name2room] for name in self.name2room]
        for name1, label, name2 in self.relation:
            if label != 0:
                relation_adj_matrix[self.name2index[name1]][self.name2index[name2]] = label
                relation_adj_matrix[self.name2index[name2]][self.name2index[name1]] = label
        return relation_adj_matrix

    def generate_relation_svg(self) -> 'Tag':
        attrs = {
            'xmlns' : 'http://www.w3.org/2000/svg', 
            'xmlns:xlink' : 'http://www.w3.org/1999/xlink', 
            'height' : self.svg_dimension[0], 
            'width' : self.svg_dimension[1]
        }
        svg = Tag('svg', attrs)
        rect = Tag('rect', {'width' : '100%', 'height' : '100%', 'fill' : 'none'})
        svg.add(rect)

        for room in self.rooms:
            svg.add(room.to_svg_polygon())
        
        for door in self.doors:
            svg.add(door.to_svg_polygon())
        
        for room1_name, label, room2_name in self.relation:
            room1 = self.name2room[room1_name]
            room2 = self.name2room[room2_name]
            if label == 0:
                continue
            line_attrs = {
                'x1' : room1.center_point[0], 
                'y1' : room1.center_point[1], 
                'x2' : room2.center_point[0], 
                'y2' : room2.center_point[1],
                'stroke' : 'grey',
                'stroke-width' : 3
            }
            if label == 2:
                line_attrs['stroke-dasharray'] = '10, 10'
            line = Tag('line', line_attrs)
            svg.add(line)
        
        for room in self.rooms:
            c_attrs = {'r' : '20', 'stroke' : 'grey', 'stroke-width' : '2'}
            c_attrs['cx'], c_attrs['cy'] = room.center_point
            c_attrs['fill'] = room_colors.get(room.type, 'grey')
            circle = Tag('circle', c_attrs)
            svg.add(circle)
    
            t_attrs = {'font-size' : '20px', 'font-family' : 'sans-serif'}
            t_attrs['x'] = c_attrs['cx'] - 50
            t_attrs['y'] = c_attrs['cy'] - 30
            t_attrs['fill'] = room_colors.get(room.type, 'grey')
            text = Tag('text', t_attrs)
            text.add(room.name)
            svg.add(text)

        return svg

    def shortest_paths_from_one_room(self, start: str) -> Dict[str, List[List[str]]]:
        adjacency_list = self.get_adjacency_list()
        queue = Queue()
        queue.put([start])
        result = {}
        while not queue.empty():
            current_path = queue.get()
            last_room = current_path[-1]
            for adjacent_room in adjacency_list[last_room]:
                if adjacent_room not in current_path:
                    new_path = current_path + [adjacent_room]
                    if adjacent_room in result:
                        if len(result[adjacent_room][0]) == len(new_path):
                            result[adjacent_room].append(new_path)
                            queue.put(new_path)
                    else:
                        result[adjacent_room] = [new_path]
                        queue.put(new_path)
        return result
    
    def shortest_paths_between_two_rooms(self, start: str, end: str) -> List[List[str]]:
        return self.shortest_paths_from_one_room(start)[end]

    def get_depth_from_one_room(self, start: str) -> int:
        adjacency_list = self.get_adjacency_list()
        queue = Queue()
        queue.put((start, 0))
        visited = set([start])
        max_depth = -1
        while not queue.empty():
            room, depth = queue.get()
            max_depth = max(max_depth, depth)
            for adjacent_room in adjacency_list[room]:
                if adjacent_room not in visited:
                    queue.put((adjacent_room, depth + 1))
                    visited.add(adjacent_room)
        return max_depth

    def get_depth(self) -> int:
        return max(self.get_depth_from_one_room(room) for room in self.room_names)
