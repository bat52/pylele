---
name: add-scad-primitive
description: Add a new scad primitive and generates adequate testing
---

To add a scad pimitive, follow this process:

0. check the openscad parser syntax and make sure the primitive exists in the scad language 

1. Add the primitive support to the B13D language core in ./src/b13d/api/core.py

2. Add a basic test in function test_api.py inside core.py, and make su

3. For each of the supported backends  (bpy,cq,mf,sp2,tm), implement suitable primitive methods

4. implement a part that makes use of the new primitive under ./b13d/parts and add the test to ./b13d/test.py making sure that test eecutes correctly

5. add parser capability for the new primitive in ./src/b1scad/scad2py.py

6. add a new scad model file making use of the new primitive under ./src/b1scad/scad and make sure it works with both openscad and b1scad

7. make sure b1scad test (./src/b1scad/test.py) runs with no errors