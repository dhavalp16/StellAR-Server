
import os
import sys
import json

# Ensure modules can be imported
sys.path.append(os.getcwd())

try:
    from modules.quiz_generator import generate_quiz_from_text
    print("Successfully imported generate_quiz_from_text")
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

# Longer sample text about the Solar System
sample_text = """
The Solar System is the gravitationally bound system of the Sun and the objects that orbit it. It formed 4.6 billion years ago from the gravitational collapse of a giant interstellar molecular cloud. The vast majority of the system's mass is in the Sun, with the majority of the remaining mass contained in Jupiter. The four inner system planets—Mercury, Venus, Earth and Mars—are terrestrial planets, being composed primarily of rock and metal. The four giant planets of the outer system are substantially more massive than the terrestrials. The two largest, Jupiter and Saturn, are gas giants, being composed mainly of hydrogen and helium; the two outermost planets, Uranus and Neptune, are ice giants, being composed mostly of substances with relatively high melting points compared with hydrogen and helium, called volatiles, such as water, ammonia and methane. All eight planets have nearly circular orbits that lie within a nearly flat disc called the ecliptic.

The Solar System also contains smaller objects. The asteroid belt, which lies between the orbits of Mars and Jupiter, mostly contains objects composed, like the terrestrial planets, of rock and metal. Beyond Neptune's orbit lie the Kuiper belt and scattered disc, which are populations of trans-Neptunian objects composed mostly of ices, and beyond them a newly discovered population of sednoids. Within these populations, some objects are large enough to have rounded under their own gravity, though there is considerable debate as to how many there will prove to be. Such objects are categorized as dwarf planets. The only certain dwarf planet is Pluto, with another trans-Neptunian object, Eris, being expected to be distinct. In addition to these two regions, various other small-body populations, including comets, centaurs and interplanetary dust clouds, freely travel between regions. Six of the planets, the six largest possible dwarf planets, and many of the smaller bodies are orbited by natural satellites, usually termed "moons" after the Moon. Each of the outer planets is encircled by planetary rings of dust and other small objects.
"""

print(f"Generating quiz from sample text ({len(sample_text)} chars)...")
print("-" * 20)
print(sample_text.strip())
print("-" * 20)

try:
    questions = generate_quiz_from_text(sample_text)
    
    print(f"\nGenerated {len(questions)} questions.")
    
    if len(questions) > 0:
        print("PASS: Questions were generated.")
        for idx, q in enumerate(questions):
            print(f"\n--- Question {idx+1} ---")
            print(json.dumps(q, indent=2))
    else:
        print("WARNING: No questions generated. Check if LLM is running/reachable.")

except Exception as e:
    print(f"An error occurred: {e}")
