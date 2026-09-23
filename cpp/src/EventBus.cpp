#include "elementchess/EventBus.hpp"

#include <utility>

namespace elementchess {

void EventBus::subscribe(Listener listener) {
    listeners_.push_back(std::move(listener));
}

void EventBus::publish(const DomainEvent& event) const {
    for (const auto& listener : listeners_) {
        listener(event);
    }
}

} // namespace elementchess
