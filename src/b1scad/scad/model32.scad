// Test let-binding
module test_let() {
    let (a = 5, b = 10) {
        cube(a);
        sphere(b);
    }
}
test_let();
