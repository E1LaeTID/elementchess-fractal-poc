#include "elementchess/Matchmaker.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace elementchess {

bool Matchmaker::compatible(const QueueEntry& a, const QueueEntry& b) noexcept {
    return a.playerId != b.playerId &&
           a.ranked == b.ranked &&
           a.rulesVersion == b.rulesVersion;
}

double Matchmaker::cost(const QueueEntry& a, const QueueEntry& b) noexcept {
    const double skillGap = std::abs(
        a.skill.conservative() - b.skill.conservative());
    const double uncertainty = 0.15 * (a.skill.deviation + b.skill.deviation);
    const double latency = 0.50 * static_cast<double>(
        std::max(a.latencyMs, b.latencyMs));
    const double regionPenalty = a.region == b.region ? 0.0 : 120.0;
    const double waitingCredit = 2.0 * static_cast<double>(
        std::min(a.waitingSeconds, b.waitingSeconds));
    return skillGap + uncertainty + latency + regionPenalty - waitingCredit;
}

std::optional<MatchCandidate> Matchmaker::findBest(
    const QueueEntry& seeker,
    const std::vector<QueueEntry>& queue) const {
    std::optional<MatchCandidate> best;
    double bestCost = std::numeric_limits<double>::infinity();

    for (const auto& entry : queue) {
        if (!compatible(seeker, entry)) {
            continue;
        }
        const double candidateCost = cost(seeker, entry);
        if (candidateCost < bestCost) {
            bestCost = candidateCost;
            best = MatchCandidate{entry.playerId, candidateCost};
        }
    }
    return best;
}

} // namespace elementchess
