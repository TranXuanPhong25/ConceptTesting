int classify_window(int value, int lower, int upper) {
    if (lower > upper) {
        return -2;
    }
    if (value < lower) {
        return -1;
    }
    if (value >= upper) {
        return 1;
    }
    return 0;
}
