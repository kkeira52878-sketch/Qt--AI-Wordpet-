#include <iostream>
#include <vector>
#include <string>
#include <iomanip>

using namespace std;

// 定义武士种类及其名称
const string WARRIOR_NAMES[5] = { "dragon", "ninja", "iceman", "lion", "wolf" };

class Headquarter {
private:
    int health_points;          // 当前生命元
    string side;                // 阵营：red 或 blue
    vector<int> order;          // 制造顺序
    vector<int> warrior_costs;  // 每种武士的消耗
    int current_idx;            // 制造顺序的指针
    int total_count;            // 制造的武士总数（编号用）
    int counts[5];              // 每种武士的数量计数
    bool stopped;               // 是否已停止制造

public:
    Headquarter(string s, int m, const vector<int>& o, const vector<int>& costs)
        : side(s), health_points(m), order(o), warrior_costs(costs) {
        current_idx = 0;
        total_count = 0;
        stopped = false;
        for (int i = 0; i < 5; ++i) counts[i] = 0;
    }

    bool isStopped() const { return stopped; }

    void tryProduce(int time) {
        if (stopped) return;

        // 尝试制造武士，最多尝试 5 次（遍历所有品种）
        for (int i = 0; i < 5; ++i) {
            int type_idx = order[current_idx];
            int cost = warrior_costs[type_idx];

            if (health_points >= cost) {
                total_count++;
                health_points -= cost;
                counts[type_idx]++;

                // 格式化输出：时间补零
                cout << setfill('0') << setw(3) << time << " "
                    << side << " " << WARRIOR_NAMES[type_idx] << " " << total_count
                    << " born with strength " << cost << "," << counts[type_idx]
                    << " " << WARRIOR_NAMES[type_idx] << " in " << side << " headquarter" << endl;

                // 指向下一个制造位置并退出本次制造
                current_idx = (current_idx + 1) % 5;
                return;
            }
            // 生命元不足，尝试下一个
            current_idx = (current_idx + 1) % 5;
        }

        // 如果循环一圈都没能制造
        stopped = true;
        cout << setfill('0') << setw(3) << time << " " << side << " headquarter stops making warriors" << endl;
    }
};

void solve(int case_num) {
    int M;
    cin >> M;
    vector<int> costs(5);
    for (int i = 0; i < 5; ++i) cin >> costs[i];

    cout << "Case:" << case_num << endl;

    // 红方顺序：iceman, lion, wolf, ninja, dragon (下标: 2, 3, 4, 1, 0)
    vector<int> red_order = { 2, 3, 4, 1, 0 };
    // 蓝方顺序：lion, dragon, ninja, iceman, wolf (下标: 3, 0, 1, 2, 4)
    vector<int> blue_order = { 3, 0, 1, 2, 4 };

    Headquarter red("red", M, red_order, costs);
    Headquarter blue("blue", M, blue_order, costs);

    int time = 0;
    while (!red.isStopped() || !blue.isStopped()) {
        red.tryProduce(time);
        blue.tryProduce(time);
        time++;
    }
}

int main() {
    int num_cases;
    if (!(cin >> num_cases)) return 0;
    for (int i = 1; i <= num_cases; ++i) {
        solve(i);
    }
    return 0;
}