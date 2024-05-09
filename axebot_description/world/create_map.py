
def create_wall(ind, c1,c2, lev, file, X_axis=True, base_height=0, max_height=1.5, thickness=0.05):
    def print_geometry():
        file.write(f"\t\t\t\t<geometry><box>\n")
        if X_axis:
            file.write(f"\t\t\t\t\t<size> {abs(c2-c1)} {thickness} {max(max_height-base_height,0)}</size>\n")
        else:
            file.write(f"\t\t\t\t\t<size> {thickness} {abs(c2-c1)} {max_height}</size>\n")
        file.write(f"\t\t\t\t</box></geometry>\n")
        if X_axis:
            file.write(f"\t\t\t\t<pose>{min(c1,c2) + abs(c2-c1)/2} {lev} {max_height/2 + base_height/2} 0 0 0</pose>\n")
        else:
            file.write(f"\t\t\t\t<pose>{lev} {min(c1,c2) + abs(c2-c1)/2} {max_height/2 + base_height/2} 0 0 0</pose>\n")
        
    file.write(f"\t\t<link name='Wall_{ind}'>\n")
    #collision
    file.write(f"\t\t\t<collision name='Wall_{ind}_Collision'>\n")
    print_geometry()
    file.write(f"\t\t\t</collision>\n")
    #visual
    file.write(f"\t\t\t<visual name='Wall_{ind}_Visual'>\n")
    print_geometry()
    file.write(f"\t\t\t\t<material>\n")
    file.write(f"\t\t\t\t\t<script><uri>file://media/materials/scripts/gazebo.material</uri><name>Gazebo/Grey</name></script>\n")
    file.write(f"\t\t\t\t\t<ambient>1 1 1 1</ambient>\n")
    file.write(f"\t\t\t\t</material>\n")
    file.write(f"\t\t\t</visual>\n")
    #end
    file.write(f"\t\t</link>\n")

def create_shell(x_sh, y_sh, name, file):
    shell = [
        1.5, -0.75,
        *([-0.4, -0.4, 0.4, -0.75] * 3),
        -1.5, 0.75,
        *([0.4, 0.4, -0.4, 0.75] * 3),
    ]
    x,y = x_sh, y_sh
    for i,sh in enumerate(shell):
        w1, w2, lev = (x, x+sh, y) if i%2==0 else (y, y+sh, x)
        create_wall(name + f'_wall_{i}', w1, w2, lev, file, X_axis=(i%2==0), max_height=1)
        x,y = (x + sh,y) if i%2==0 else (x, y+sh)


file = open('Storage_map/model.sdf', 'w')
print(file)
#write header
file.write("<?xml version='1.0'?>\n")
file.write("<sdf version='1.7'>\n")
file.write("\t<model name='Storage_map'>\n")

# model discription
file.write(f"\t\t<pose>0 0 0 0 0 0</pose>\n")
file.write(f"\t\t<static>1</static>\n")

# walls
create_wall(  'up_1', -4.5,-4.25,   3, file, X_axis=True)
create_wall(  'up_2',-4.25,-3.45,   3, file, X_axis=True, base_height=1.15)
create_wall(  'up_3',-3.45,  4.5,   3, file, X_axis=True)
create_wall( 'right',    3,   -3, 4.5, file, X_axis=False)
create_wall('down_1',  4.5,-3.45,  -3, file, X_axis=True)
create_wall('down_2',-3.45,-4.25,  -3, file, X_axis=True, base_height=1.15)
create_wall('down_3',-4.25, -4.5,  -3, file, X_axis=True)
create_wall(  'left',   -3,    3,-4.5, file, X_axis=False)

#shells
ys = 3 - 1.1
xl = -4.5
x1 = xl + 1.28
x2 = x1 + 1.5 + 1.26
x3 = x2 + 1.5 + 1.26
create_shell(x1, ys, "shell_0", file)
create_shell(x2, ys, "shell_1", file)
create_shell(x3, ys, "shell_2", file)

#write end
file.write("\t</model>\n")
file.write("</sdf>")