'''
Provides the AbstractBoard class, which keeps track of an sgf game
and logical board and returns the moves made whilst moving through the
game tree.

'''

from gomill import sgf, boards

def get_markers_from_node(node):
    properties = node.properties()
    instructions = {'marker':[]}
    markers = []
    if 'TR' in properties:
        node_markers = node.find_property('TR')
        for marker in node_markers:
            markers.append((marker,'TR'))
    if 'SQ' in properties:
        node_markers = node.find_property('SQ')
        for marker in node_markers:
            markers.append((marker,'SQ'))
    if 'CR' in properties:
        node_markers = node.find_property('CR')
        for marker in node_markers:
            markers.append((marker,'CR'))
    if 'MA' in properties:
        node_markers = node.find_property('MA')
        for marker in node_markers:
            markers.append((marker,'MA'))
    if 'LB' in properties:
        node_markers = node.find_property('LB')
        for marker in node_markers:
            markers.append((marker[0],'LB',marker[1]))
        

    if len(markers) > 0:
        return {'markers': markers}
    else:
        return {}

def get_setupstones_from_node(node):
    print 'Getting setupstones!'
    black, white, empty = node.get_setup_stones()
    stones = []
    for stone in black:
        stones.append((stone,'b'))
    for stone in white:
        stones.append((stone,'w'))
    for stone in empty:
        stones.append((stone,'e'))
    print 'setup stones returned:', stones
    return stones
        

def apply_node_to_board(board, node):
    board = board.copy()
    add_stones = []
    remove_stones = []
    empty_stones = []
    add_playmarker = None

    current_occupied_points = board.list_occupied_points()

    # First, find and deal with setup stones
    if node.has_setup_stones():
        print '### Node has setup stones!'
        setup_stones = get_setupstones_from_node(node)
        if len(setup_stones) > 0:
            for stone in setup_stones:
                coords,col = stone
                if col in ['b','w']:
                    board.board[coords[0]][coords[1]] = col
                elif col == 'e':
                    board.board[coords[0]][coords[1]] = None
            

    # Now deal with the actual new move, if any

    new_move_colour, new_move_point = node.get_move()
    if new_move_point is not None:
        try:
            board.play(new_move_point[0],new_move_point[1],new_move_colour)
            add_playmarker = new_move_point
        except ValueError:
            print 'SGF played existing point'
    new_occupied_points = board.list_occupied_points()
    if len(new_occupied_points) == len(current_occupied_points) + 1:
        add_stones.append((new_move_point, new_move_colour))
    else:
        for point in new_occupied_points:
            if point not in current_occupied_points:
                add_stones.append((point[1],point[0]))
        for point in current_occupied_points:
            if point not in new_occupied_points:
                remove_stones.append((point[1],point[0]))


    instructions = {}
    if len(add_stones) > 0:
        instructions['add'] = add_stones
    if len(remove_stones) > 0:
        instructions['remove'] = remove_stones
    if len(empty_stones) > 0:
        instructions['empty'] = empty_stones
    if add_playmarker is not None:
        instructions['playmarker'] = add_playmarker

    node_markers = get_markers_from_node(node)
    instructions.update(node_markers)

    #instructions.update(setup_stones)

    return (board, instructions)



def compare_boards(old, new):
    add_stones = []
    remove_stones = []

    old_stones = old.list_occupied_points()
    new_stones = new.list_occupied_points()
    for point in new_stones:
        if point not in old_stones:
            add_stones.append((point[1],point[0]))
    for point in old_stones:
        if point not in new_stones:
            remove_stones.append((point[1],point[0]))

    instructions = {}
    if len(add_stones) > 0:
        instructions['add'] = add_stones
    if len(remove_stones) > 0:
        instructions['remove'] = remove_stones

    return instructions

    

class AbstractBoard(object):
    def __init__(self,game=None):
        if game is None:
            game = sgf.Sgf_game(19)

        self.game = game
        self.prisoners = [0,0]
        self.variation_index = 0

        self.boards = {}
        self.curnode = game.get_root()
        self.boards[self.curnode] = boards.Board(self.game.size)

    def load_sgf_from_file(self,filen):
        fileh = open(filen,'r')
        sgfdata = fileh.read()
        fileh.close()
        self.game = sgf.Sgf_game.from_string(sgfdata)
        self.reset_position()

    def load_sgf_from_text(self, sgftext):
        self.game = sgf.Sgf_game.from_string(sgftext)
        self.reset_position()

    def set_sgf(self,sgf):
        self.game = sgf
        self.reset_position()

    def reset_position(self):
        self.curnode = self.game.get_root()
        self.boards = {}
        self.boards[self.curnode] = boards.Board(self.game.size)

    def advance_position(self,*args,**kwargs):
        curnode = self.curnode
        curboard = self.boards[curnode]
        if len(curnode) > 0:
            newnode = self.curnode[0]
        else:
            return {}

        self.curnode = newnode
        newboard = curboard.copy()

        
        newboard, instructions = apply_node_to_board(newboard, newnode)

        self.boards[newnode] = newboard

        return instructions


    def retreat_position(self,*args,**kwargs):
        curnode = self.curnode
        curboard = self.boards[curnode]
        if curnode.parent is not None:
            newnode = self.curnode.parent
        else:
            return {}

        self.curnode = newnode
        if self.boards.has_key(newnode):
            newboard = self.boards[newnode]
        else:
            print 'Reconstruct board'

        self.boards[newnode] = newboard

        instructions = compare_boards(curboard, newboard)

        newmove = newnode.get_move()
        if newmove[1] is not None:
            instructions['playmarker'] = newmove[1]

        markers = get_markers_from_node(newnode)
        if len(markers) > 0:
            instructions.update(markers)

        return instructions

    def increment_variation(self):
        if self.curnode.parent is not None:
            parentnode = self.curnode.parent
            newnode = parentnode[(parentnode.index(self.curnode)+1) % len(parentnode)]
            return self.jump_to_node(newnode)
        else:
            return {}

    def decrement_variation(self):
        if self.curnode.parent is not None:
            parentnode = self.curnode.parent
            newnode = parentnode[(parentnode.index(self.curnode)-1) % len(parentnode)]
            return self.jump_to_node(newnode)
        else:
            return {}
            
            

    def jump_to_node(self,node):
        oldboard = self.boards[self.curnode]
        self.curnode = node
        newboard = self.get_or_build_board(node)
        instructions = compare_boards(oldboard,newboard)
        newmove = node.get_move()
        if newmove[1] is not None:
            instructions['playmarker'] = newmove[1]
        return instructions
            

    def get_or_build_board(self, node):
        if not self.boards.has_key(node):
            self.build_boards_to_node(node)
        return self.boards[node]

    def build_boards_to_node(self, node, replace=False):
        precursor_nodes = self.game.get_sequence_above(node)
        board = boards.Board(self.game.size)
        board, instructions = apply_node_to_board(board,precursor_nodes[0])
        self.boards[precursor_nodes[0]] = board

        for i in range(1,len(precursor_nodes)):
            curnode = precursor_nodes[i]
            if (not self.boards.has_key(curnode)) or replace:
                board, instructions = apply_node_to_board(board, curnode)
                self.boards[curnode] = board
            else:
                board = self.boards[curnode]

        curnode = node
        board, instructions = apply_node_to_board(board, node)
        self.boards[node] = board


        
