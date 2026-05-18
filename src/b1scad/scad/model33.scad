// model33: nested scopes and variable shadowing
// Test that variables defined inside a module body don't leak to outer scope
x = 10;

module test() {
    y = 5;
    cube(y);
}

test();
// x should still be 10 here, and y should not be visible
cube(x);
