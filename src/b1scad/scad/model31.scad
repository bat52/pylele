module wrap() {
    children();
}
module box_children() {
    cube(10);
    children();
}
wrap() sphere(5);
box_children() cylinder(h=5, r1=3, r2=3);
