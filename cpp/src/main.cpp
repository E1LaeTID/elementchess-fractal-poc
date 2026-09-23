#include <SFML/Graphics.hpp>

int main() {
    sf::RenderWindow window(sf::VideoMode({1280, 720}), "ElementChess");
    window.setVerticalSyncEnabled(true);

    while (window.isOpen()) {
        while (const auto event = window.pollEvent()) {
            if (event->is<sf::Event::Closed>()) {
                window.close();
            }
        }
        window.clear(sf::Color(15, 20, 26));
        window.display();
    }
}
