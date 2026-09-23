#pragma once

#include <cstdint>
#include <string>
#include <variant>

namespace elementchess {

enum class Player : std::uint8_t { white, black };

struct PieceMoved {
    Player player{};
    std::uint8_t fromX{};
    std::uint8_t fromY{};
    std::uint8_t toX{};
    std::uint8_t toY{};
};

struct CombatResolved {
    Player attacker{};
    bool rejected{};
    std::uint32_t attackPower{};
    std::uint32_t defensePower{};
};

struct MatchEnded {
    Player winner{};
    std::string reason;
};

using EventPayload = std::variant<PieceMoved, CombatResolved, MatchEnded>;

struct DomainEvent {
    std::uint64_t sequence{};
    std::string rulesVersion;
    EventPayload payload;
};

} // namespace elementchess
