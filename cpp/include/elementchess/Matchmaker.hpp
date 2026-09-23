#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace elementchess {

struct SkillRating {
    double rating{1500.0};
    double deviation{350.0};
    double volatility{0.06};

    [[nodiscard]] double conservative() const noexcept {
        return rating - 2.0 * deviation;
    }
};

struct QueueEntry {
    std::uint64_t playerId{};
    SkillRating skill{};
    std::uint32_t latencyMs{};
    std::uint32_t waitingSeconds{};
    std::string region;
    std::string rulesVersion;
    bool ranked{};
};

struct MatchCandidate {
    std::uint64_t opponentId{};
    double cost{};
};

class Matchmaker {
public:
    [[nodiscard]] std::optional<MatchCandidate> findBest(
        const QueueEntry& seeker,
        const std::vector<QueueEntry>& queue) const;

private:
    [[nodiscard]] static bool compatible(
        const QueueEntry& a, const QueueEntry& b) noexcept;
    [[nodiscard]] static double cost(
        const QueueEntry& a, const QueueEntry& b) noexcept;
};

} // namespace elementchess
