// model30.scad - Test intersection_for operation
// Spheres overlap so intersection is non-empty
intersection_for(i = [0:2]) {
    translate([i*5,0,0]) {
        sphere(8);
    }
}
