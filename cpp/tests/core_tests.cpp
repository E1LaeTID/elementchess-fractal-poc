#include "elementchess/EventBus.hpp"
#include "elementchess/Matchmaker.hpp"

#include <cassert>
#include <string>
#include <vector>

int main() {
    using namespace elementchess;

    EventBus bus;
    std::uint64_t received = 0;
    bus.subscribe([&received](const DomainEvent& event) {
        received = event.sequence;
    });
    bus.publish(DomainEvent{7, "0.26", PieceMoved{Player::white, 1, 1, 1, 3}});
    assert(received == 7);

    const QueueEntry seeker{1, {1500, 80, 0.06}, 35, 10, "eu", "0.26", true};
    const std::vector<QueueEntry> queue{
        {2, {1510, 75, 0.06}, 40, 8, "eu", "0.26", true},
        {3, {1900, 50, 0.06}, 20, 8, "eu", "0.26", true},
        {4, {1500, 75, 0.06}, 30, 8, "eu", "0.27", true}
    };
    const auto match = Matchmaker{}.findBest(seeker, queue);
    assert(match.has_value());
    assert(match->opponentId == 2);

    return 0;
}
