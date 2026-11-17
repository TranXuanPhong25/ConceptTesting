#include <fstream>
#include <sstream>
#include <iomanip>
#include <vector>
#include <map>
#include <string>
#include <cmath>
#include <stdexcept>
#include <boost/any.hpp>
// JSON result channel is independent of target stdout.
std::string ct_json(const std::string& value) {
    std::ostringstream out; out << '"';
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') { out << '\\' << c; }
        else if (c < 32) { out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << int(c) << std::dec; }
        else { out << c; }
    }
    out << '"'; return out.str();
}
std::string ct_json(const bool& value) { return value ? "true" : "false"; }
std::string ct_json(const boost::any& value) {
    if (value.type() == typeid(bool)) return ct_json(boost::any_cast<bool>(value));
    if (value.type() == typeid(int)) return ct_json(boost::any_cast<int>(value));
    if (value.type() == typeid(float)) return ct_json(boost::any_cast<float>(value));
    if (value.type() == typeid(double)) return ct_json(boost::any_cast<double>(value));
    if (value.type() == typeid(std::string)) return ct_json(boost::any_cast<std::string>(value));
    throw std::runtime_error("unsupported boost::any output");
}
std::string ct_json(const char& value) { return ct_json(std::string(1,value)); }
template <typename T> std::string ct_json(const T& value) {
    if (!std::isfinite(double(value))) throw std::runtime_error("nonfinite output");
    std::ostringstream out; out << std::setprecision(17) << value; return out.str();
}
template <typename T> std::string ct_json(const std::vector<T>& value);
template <typename K, typename V> std::string ct_json(const std::map<K,V>& value);
template <typename T> std::string ct_json(const std::vector<T>& value) {
    std::string out="["; bool first=true;
    for (const auto& item: value) { if (!first) out += ","; first=false; out += ct_json(item); }
    return out + "]";
}
template <typename K, typename V> std::string ct_json(const std::map<K,V>& value) {
    std::string out="{"; bool first=true;
    for (const auto& item: value) { if (!first) out += ","; first=false; out += ct_json(item.first) + ":" + ct_json(item.second); }
    return out + "}";
}
template <typename T> void ct_write(const T& value) { std::ofstream out("/results/ct-result.json"); out << ct_json(value); }
int main(int argc,char** argv) {
    if (argc != 2) return 2;
    switch(std::stoi(argv[1])) { /* CALLS */ default: return 3; }
}
