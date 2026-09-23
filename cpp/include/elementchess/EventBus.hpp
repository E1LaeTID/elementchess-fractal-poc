#pragma once

#include "elementchess/Event.hpp"

#include <functional>
#include <vector>

namespace elementchess {

class EventBus {
public:
    using Listener = std::function<void(const DomainEvent&)>;

    void subscribe(Listener listener);
    void publish(const DomainEvent& event) const;

private:
    std::vector<Listener> listeners_;
};

} // namespace elementchess
