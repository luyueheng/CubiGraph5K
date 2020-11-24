# Author: Yueheng Lu <luyueheng.arch@gmail.com>

# Imports
from typing import List, Tuple, Dict
from shapely.geometry import Polygon
from bs4 import BeautifulSoup
from bs4.element import Tag as bs4Tag
from collections import defaultdict


room_colors = {
    # map from class name (after Space)
    # color the ones interested
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
        self.adjacent_doors = set()
        self.neighbours=[]
        self.level={}
        self.parent={}

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
        plg_attrs = {'fill' : 'none','stroke' : 'black', 'stroke-width' : 2}
        plg_attrs['points'] = ' '.join(['{},{}'.format(p[0], p[1]) for p in self.points])
        return Tag('polygon', plg_attrs)

    def to_shapely_polygon(self) -> Polygon:
        return Polygon(self.points)


class Plan:

    def __init__(self, dataPath,id):
        self.path=dataPath+'/{}/model.svg'.format(id)
        with open(self.path) as f:
            content = f.read(1000000)
        soup = BeautifulSoup(content, 'lxml')
        self.svg=soup.find('svg')
        self.rooms = [] # parse from svg
        self.name2room = {}
        self.doors = [] # parse from svg
        self.name2door = {}
        self.relation = [] # generate by calling self.generate_room_relation()
        self.room_type_count = defaultdict(int)
        self.door_count = 0
        self.svg_dimension = (self.svg.attrs['height'], self.svg.attrs['width'])
        self.roomNames=[]
        self.adjList=self.get_adjacency_list()
        self.vertices={} 

        for r in self.svg.find_all('g', attrs={'class': 'Space'}):
            room = Room(r, self.room_type_count)
            self.rooms.append(room)
            self.name2room[room.name] = room
            self.roomNames.append(room.name)

        for d in self.svg.find_all('g', attrs={'class': 'Threshold'}):
            door = Door(d, self.door_count)
            self.doors.append(door)
            self.door_count += 1
            self.name2door[door.name] = door
    
    def generate_room_relation(self) -> None:
        for room in self.rooms:
            room.get_adjacent_doors(self.doors)
            self.add_vertex(room)
        
        for i in range(len(self.rooms)):
            for j in range(i+1, len(self.rooms)):
                room1 = self.rooms[i]
                room2 = self.rooms[j]
                if room1.to_shapely_polygon().buffer(1.0).intersection(room2.to_shapely_polygon().buffer(1.0)).area > 5.0:
                # if room1.to_shapely_polygon().overlaps(room2.to_shapely_polygon()):
                    self.relation.append((room1.name, 1, room2.name))
                elif room1.adjacent_doors.intersection(room2.adjacent_doors):
                    self.relation.append((room1.name, 2, room2.name))
                else:
                    self.relation.append((room1.name, 0, room2.name))
        self.get_neighbours()

    def get_adjacency_list(self) -> dict:
        relation_adj_list = {name : {} for name in self.name2room}
        for name1, label, name2 in self.relation:
            if label != 0:
                relation_adj_list[name1][name2] = label
                relation_adj_list[name2][name1] = label
        return relation_adj_list

    def get_neighbours(self) -> None:
        for room in self.rooms:
            room.get_adjacent_doors(self.doors)
        
        for i in range(len(self.rooms)):
            room1 = self.rooms[i]
            for j in range(0, len(self.rooms)):
                room2 = self.rooms[j]
                if room1.to_shapely_polygon().buffer(1.0).intersection(room2.to_shapely_polygon().buffer(1.0)).area > 5.0:
                    if room2.name !=room1.name:
                        room1.neighbours.append(room2)
                elif room1.adjacent_doors.intersection(room2.adjacent_doors):
                    if room2.name !=room1.name:
                        room1.neighbours.append(room2)

    def add_vertex(self,room): # add vertex(room instance) into the graph
        if isinstance(room, Room) and room.name not in self.vertices:
            self.vertices[room.name]=room
            return True
        else:
            return False
     
    def print_graph(self):
        for key in list(self.vertices.keys()):
            print(key + ': '+str([n.name for n in self.vertices[key].neighbours])+'\n')
                

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
            t_attrs['x'] = c_attrs['cx'] - 30
            t_attrs['y'] = c_attrs['cy'] - 30
            text = Tag('text', t_attrs)
            text.add(room.name)
            svg.add(text)

        return svg
    
    def explore(self,s):
        levels={s:0}
        i=1
        frontier=[s]
        while frontier:
            # print(frontier)
            nxt=[]
            for u in frontier:
                for v in u.neighbours:
                    if v not in levels:
                        levels[v]=i
                        v.level=i
                        v.parent[v.name]=u
                        nxt.append(v)
            frontier=nxt
            i+=1
            out={}
            for l in levels:
                out[l.name]=levels[l]
        return out

    def bt(self,answers, answer, path):
        if len(answer)==len(path):
            answers.append(answer[:])
            return
        for p in path[len(answer)]:
            answer.append(p)
            self.bt(answers,answer,path)
            answer.pop()
    
    def get_all_paths(self,path):
        answers, answer=[],[]
        self.bt(answers, answer, path)
        return answers

    def shortest_path(self,s,t):
        self.explore(s)
        path=[[t.name]]
        if not t.parent:
            print('No path')
            return
        else:
            while t.parent[t.name].name!=s.name:
                nxt=[]
                for n in t.neighbours:
                    if n.level==t.level-1 and n.parent[n.name]==t.parent[t.name].parent[t.parent[t.name].name]:
                        nxt.append(n.name)
                path.append(nxt)
                t=t.parent[t.name]
            path.append([s.name])
            path.reverse()
        return self.get_all_paths(path)


def main():
    n = 41
    # input_path = '../data_lyh/cubicasa5k/high_quality_architectural/{}/model.svg'.format(n)
    input_path = 'C:/Users/ao/Desktop/dataProjectI/CubiGraph5K-main/CubiGraph5K-main/data'
    output_path = 'C:/Users/ao/Desktop/dataProjectI/CubiGraph5K-main/CubiGraph5K-main/data/svg/{}.svg'.format(n)

    
    # with open(input_path) as f:
    #     content = f.read(1000000)
    # soup = BeautifulSoup(content, 'lxml')

    plan = Plan(input_path,n)
    plan.generate_room_relation()
    # print(plan.name2room['Entry_1'].to_shapely_polygon().buffer(1.0).intersection(plan.name2room['Kitchen_1'].to_shapely_polygon().buffer(1.0)).area)
    # print(list(plan.name2room['LivingRoom_1'].adjacent_doors)[0])
    # print(plan.name2door[list(plan.name2room['LivingRoom_1'].adjacent_doors)[0]].to_shapely_polygon().buffer(1.0).intersection(plan.name2room['Kitchen_1'].to_shapely_polygon()).area)
    # print(plan.name2door[list(plan.name2room['LivingRoom_1'].adjacent_doors)[0]].to_shapely_polygon().buffer(1.0).intersection(plan.name2room['LivingRoom_1'].to_shapely_polygon()).area)
    # print(plan.roomNames)
    print(plan.rooms[1].neighbours)
    plan.print_graph()
    s=plan.vertices['Bedroom_2']
    e=plan.vertices['Bedroom_3']
    print(plan.shortest_path(s,e))
    with open(output_path, 'w') as output:
        output.write(str(plan.generate_relation_svg()))
    

if __name__ == "__main__":
    main()
