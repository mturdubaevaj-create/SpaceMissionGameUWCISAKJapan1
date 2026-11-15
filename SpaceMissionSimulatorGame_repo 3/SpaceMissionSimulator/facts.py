"""NASA / space fact database used by the friendly alien, the alien pirate and
the stranded astronaut.

Each fact has:
  text     - the fact as the friendly alien tells it
  cat      - category
  q        - multiple-choice question (pirate)
  options  - 4 answers, the FIRST one is correct (shuffled in game)
  true_s   - a true statement (genuine astronaut)
  false_s  - a false statement (alien impostor)
Add new facts by appending to FACTS.
"""
import random

FACTS = [
    dict(id="armstrong", cat="Astronauts",
         text="On 20 July 1969, Neil Armstrong became the first human to walk on the Moon during Apollo 11.",
         q="Who was the first human to walk on the Moon?",
         options=["Neil Armstrong", "Buzz Aldrin", "Yuri Gagarin", "Michael Collins"],
         true_s="Neil Armstrong was the first human to walk on the Moon, in 1969.",
         false_s="Buzz Aldrin was the first human to step onto the Moon."),
    dict(id="nasa1958", cat="NASA",
         text="NASA was founded in 1958, one year after the Soviet Union launched Sputnik 1.",
         q="In which year was NASA founded?",
         options=["1958", "1969", "1947", "1962"],
         true_s="NASA was founded in 1958.",
         false_s="NASA was founded in 1969, the year of the first Moon landing."),
    dict(id="gagarin", cat="Space history",
         text="Yuri Gagarin was the first human in space. He orbited Earth in Vostok 1 in 1961.",
         q="Who was the first human in space?",
         options=["Yuri Gagarin", "John Glenn", "Alan Shepard", "Neil Armstrong"],
         true_s="Yuri Gagarin became the first person in space in 1961.",
         false_s="John Glenn was the very first human to travel to space."),
    dict(id="iss90", cat="Spacecraft",
         text="The International Space Station circles Earth about every 90 minutes - around 16 sunrises a day!",
         q="Roughly how long does the ISS take to orbit Earth once?",
         options=["About 90 minutes", "About 24 hours", "About 12 hours", "About 10 minutes"],
         true_s="The ISS orbits the Earth roughly every 90 minutes.",
         false_s="The ISS takes a full 24 hours to orbit the Earth once."),
    dict(id="escape", cat="Physics",
         text="To escape Earth's gravity completely you need to reach about 11.2 km/s - the escape velocity.",
         q="What is Earth's escape velocity?",
         options=["About 11.2 km/s", "About 3 km/s", "About 1 km/s", "About 100 km/s"],
         true_s="Earth's escape velocity is about 11.2 kilometres per second.",
         false_s="Earth's escape velocity is only about 3 kilometres per second."),
    dict(id="venushot", cat="Planets",
         text="Venus is the hottest planet (about 465 C) even though Mercury is closer to the Sun. Its thick CO2 air traps heat.",
         q="Which is the hottest planet in the Solar System?",
         options=["Venus", "Mercury", "Mars", "Jupiter"],
         true_s="Venus is hotter than Mercury because its thick atmosphere traps heat.",
         false_s="Mercury is the hottest planet because it is closest to the Sun."),
    dict(id="venusday", cat="Planets",
         text="A day on Venus (243 Earth days) is longer than its year (225 Earth days). It spins very slowly - and backwards!",
         q="On Venus, which is longer?",
         options=["Its day is longer than its year", "Its year is longer than its day",
                  "They are exactly equal", "Venus does not rotate"],
         true_s="One day on Venus lasts longer than one Venus year.",
         false_s="Venus spins much faster than Earth, so its days are only a few hours long."),
    dict(id="olympus", cat="Planets",
         text="Olympus Mons on Mars is the tallest volcano in the Solar System, about 2.5 times the height of Mount Everest.",
         q="Where is Olympus Mons, the Solar System's tallest volcano?",
         options=["Mars", "Venus", "Earth", "The Moon"],
         true_s="The tallest volcano in the Solar System, Olympus Mons, is on Mars.",
         false_s="Mount Everest is the tallest mountain in the whole Solar System."),
    dict(id="redspot", cat="Planets",
         text="Jupiter's Great Red Spot is a giant storm wider than Earth that has raged for centuries.",
         q="What is Jupiter's Great Red Spot?",
         options=["A giant storm", "A volcano", "An impact crater", "A frozen ocean"],
         true_s="Jupiter's Great Red Spot is a storm bigger than the Earth.",
         false_s="Jupiter's Great Red Spot is a huge volcano on its rocky surface."),
    dict(id="saturnfloat", cat="Planets",
         text="Saturn's average density is lower than water's. In a giant enough bathtub, it would float!",
         q="Which planet is less dense than water?",
         options=["Saturn", "Earth", "Mars", "Mercury"],
         true_s="Saturn is less dense than water.",
         false_s="Saturn is the densest planet in the Solar System."),
    dict(id="light8", cat="Astronomy",
         text="Sunlight takes about 8 minutes 20 seconds to reach Earth. You always see the Sun as it was 8 minutes ago.",
         q="How long does sunlight take to reach Earth?",
         options=["About 8 minutes", "About 8 seconds", "About 8 hours", "Instantly"],
         true_s="Light from the Sun takes a little over 8 minutes to reach Earth.",
         false_s="Light from the Sun reaches Earth in about 8 seconds."),
    dict(id="voyager", cat="Spacecraft",
         text="Voyager 1, launched in 1977, entered interstellar space in 2012. It is the farthest human-made object.",
         q="Which spacecraft is the farthest human-made object from Earth?",
         options=["Voyager 1", "Hubble", "Apollo 11", "Sputnik 1"],
         true_s="Voyager 1 is the most distant human-made object.",
         false_s="The Hubble Space Telescope is the farthest object humans have built."),
    dict(id="hubble", cat="Spacecraft",
         text="The Hubble Space Telescope was launched in 1990 by Space Shuttle Discovery and was repaired by astronauts 5 times.",
         q="What carried the Hubble Space Telescope into orbit in 1990?",
         options=["Space Shuttle Discovery", "A Saturn V rocket", "Falcon 9", "Soyuz"],
         true_s="Hubble was launched in 1990 aboard Space Shuttle Discovery.",
         false_s="Hubble was launched on a Saturn V rocket in 1975."),
    dict(id="jwst", cat="Spacecraft",
         text="The James Webb Space Telescope launched on 25 Dec 2021. It mostly sees infrared light, letting it look through dust.",
         q="What kind of light does the James Webb Space Telescope mainly observe?",
         options=["Infrared", "X-rays", "Radio waves", "Ultraviolet only"],
         true_s="The James Webb Space Telescope mainly observes infrared light.",
         false_s="The James Webb Space Telescope is an X-ray telescope."),
    dict(id="saturnv", cat="Spacecraft",
         text="The Saturn V rocket, about 110 m tall, launched the Apollo astronauts to the Moon.",
         q="Which rocket launched the Apollo astronauts to the Moon?",
         options=["Saturn V", "Falcon 9", "Ariane 5", "The Space Shuttle"],
         true_s="Apollo astronauts flew to the Moon on top of Saturn V rockets.",
         false_s="Apollo astronauts travelled to the Moon aboard the Space Shuttle."),
    dict(id="ingenuity", cat="Spacecraft",
         text="Mars rover Perseverance carried a small helicopter, Ingenuity, which made the first powered flight on another planet in 2021.",
         q="What was the name of the first helicopter to fly on Mars?",
         options=["Ingenuity", "Curiosity", "Spirit", "Dragonfly"],
         true_s="The helicopter Ingenuity made the first powered flight on another planet.",
         false_s="The Curiosity rover carried the first helicopter to Mars in 2012."),
    dict(id="marsred", cat="Planets",
         text="Mars looks red because its dust and rocks contain lots of iron oxide - rust!",
         q="Why does Mars look red?",
         options=["Iron oxide (rust) in its dust", "Red ice caps", "Red oceans",
                  "Reflected light from Jupiter"],
         true_s="Mars is red because its soil is full of iron oxide, which is rust.",
         false_s="Mars is red because it is covered in red frozen oceans."),
    dict(id="shuttle", cat="Spacecraft",
         text="NASA's Space Shuttle flew 135 missions from 1981 to 2011. It was a reusable spaceplane for low Earth orbit.",
         q="During which years did the Space Shuttle fly?",
         options=["1981 - 2011", "1961 - 1972", "1990 - 2020", "1969 - 1975"],
         true_s="The Space Shuttle flew 135 missions between 1981 and 2011.",
         false_s="The Space Shuttle was regularly used to fly astronauts to the Moon."),
    dict(id="moong", cat="Planets",
         text="Gravity on the Moon is about one-sixth of Earth's. You could jump about six times higher there!",
         q="How strong is the Moon's gravity compared to Earth's?",
         options=["About 1/6", "About 1/2", "About the same", "About 2x"],
         true_s="The Moon's gravity is about one-sixth as strong as Earth's.",
         false_s="The Moon's gravity is about half as strong as Earth's."),
    dict(id="horizon", cat="Astronomy",
         text="A black hole's event horizon is the boundary beyond which nothing - not even light - can escape.",
         q="What can escape from inside a black hole's event horizon?",
         options=["Nothing, not even light", "Only light", "Only radio waves", "Spacecraft at full speed"],
         true_s="Nothing, not even light, can escape from inside the event horizon.",
         false_s="Light can still escape from inside a black hole's event horizon."),
    dict(id="eht", cat="Astronomy",
         text="In 2019 the Event Horizon Telescope - a network of radio dishes across Earth - captured the first image of a black hole (M87*).",
         q="Which project captured the first image of a black hole?",
         options=["Event Horizon Telescope", "Hubble", "Kepler", "Apollo 13"],
         true_s="The first image of a black hole was captured by the Event Horizon Telescope in 2019.",
         false_s="The first photo of a black hole was taken by astronauts on Apollo 13."),
    dict(id="kepler", cat="Astronomy",
         text="NASA's Kepler telescope found thousands of exoplanets by watching stars dim slightly as planets passed in front - the transit method.",
         q="How did the Kepler telescope detect most of its exoplanets?",
         options=["Watching stars dim as planets pass", "Taking close-up photos",
                  "Sending probes to them", "Listening for radio signals"],
         true_s="Kepler found exoplanets by measuring tiny dips in starlight during transits.",
         false_s="Kepler found exoplanets by flying to other star systems and photographing them."),
    dict(id="parker", cat="Spacecraft",
         text="NASA's Parker Solar Probe has flown closer to the Sun than any other spacecraft, through the Sun's outer atmosphere.",
         q="Which spacecraft has flown closest to the Sun?",
         options=["Parker Solar Probe", "Voyager 2", "Juno", "Cassini"],
         true_s="The Parker Solar Probe has flown closer to the Sun than any other spacecraft.",
         false_s="No spacecraft has ever flown closer to the Sun than the planet Mercury."),
    dict(id="dawn", cat="Spacecraft",
         text="NASA's Dawn mission used ion engines to orbit two worlds in the asteroid belt: Vesta and Ceres.",
         q="Which mission used ion engines to orbit both Vesta and Ceres?",
         options=["Dawn", "Apollo 11", "Viking 1", "New Horizons"],
         true_s="The Dawn spacecraft used ion propulsion to visit Vesta and Ceres.",
         false_s="Ion engines are powerful enough to launch rockets from Earth's surface."),
    dict(id="isp", cat="Physics",
         text="Specific impulse (Isp) measures how efficiently an engine uses propellant. Higher Isp = more speed change per kilogram of fuel.",
         q="What does an engine's specific impulse measure?",
         options=["How efficiently it uses propellant", "How loud it is",
                  "How hot the fuel is", "How tall the rocket is"],
         true_s="A higher specific impulse means an engine uses its propellant more efficiently.",
         false_s="Specific impulse measures the colour of a rocket's flame."),
    dict(id="karman", cat="Space history",
         text="The Karman line, 100 km above sea level, is commonly used as the boundary where space begins.",
         q="At roughly what altitude is the Karman line, the edge of space?",
         options=["100 km", "10 km", "1,000 km", "36,000 km"],
         true_s="The Karman line, often called the edge of space, is about 100 km up.",
         false_s="Space officially begins just 10 km above the ground."),
    dict(id="ikaros", cat="Spacecraft",
         text="Japan's JAXA flew IKAROS in 2010 - the first spacecraft to show a solar sail working in interplanetary space.",
         q="Which space agency flew IKAROS, the first interplanetary solar sail?",
         options=["JAXA (Japan)", "ESA (Europe)", "NASA (USA)", "ISRO (India)"],
         true_s="JAXA's IKAROS was the first spacecraft to demonstrate a solar sail between the planets.",
         false_s="Solar sails need large amounts of rocket fuel to work."),
    dict(id="tereshkova", cat="Astronauts",
         text="Valentina Tereshkova became the first woman in space in 1963. Sally Ride became the first American woman in space in 1983.",
         q="Who was the first woman in space?",
         options=["Valentina Tereshkova", "Sally Ride", "Mae Jemison", "Peggy Whitson"],
         true_s="Valentina Tereshkova was the first woman to fly in space, in 1963.",
         false_s="Sally Ride was the very first woman in space."),
    dict(id="bennu", cat="Spacecraft",
         text="NASA's OSIRIS-REx collected rock and dust from asteroid Bennu and returned it to Earth in 2023.",
         q="Which asteroid did OSIRIS-REx bring samples back from?",
         options=["Bennu", "Ceres", "Vesta", "Halley"],
         true_s="OSIRIS-REx brought samples from asteroid Bennu back to Earth in 2023.",
         false_s="OSIRIS-REx brought samples back from the planet Mars."),
    dict(id="dart", cat="NASA",
         text="In 2022 NASA's DART spacecraft deliberately crashed into the asteroid moonlet Dimorphos and changed its orbit - the first planetary defence test.",
         q="What did NASA's DART mission do in 2022?",
         options=["Changed an asteroid's orbit by impact", "Landed on Mars",
                  "Photographed a black hole", "Repaired Hubble"],
         true_s="NASA's DART mission changed the orbit of an asteroid moonlet by crashing into it.",
         false_s="NASA's DART mission blew up an asteroid with a nuclear bomb."),
    dict(id="sunmass", cat="Astronomy",
         text="The Sun contains about 99.8% of all the mass in our Solar System.",
         q="About how much of the Solar System's mass is in the Sun?",
         options=["About 99.8%", "About 50%", "About 75%", "About 10%"],
         true_s="The Sun holds about 99.8 percent of the Solar System's mass.",
         false_s="Jupiter holds more mass than the Sun."),
    dict(id="artemis", cat="NASA",
         text="NASA's Artemis program, returning humans to the Moon, is named after Apollo's twin sister in Greek mythology.",
         q="In Greek mythology, who was Artemis?",
         options=["Apollo's twin sister", "Zeus's father", "Goddess of the sea", "Mars's brother"],
         true_s="The Artemis program is named after the twin sister of Apollo.",
         false_s="The Artemis program is named after the first dog to orbit the Moon."),
    dict(id="taller", cat="Astronauts",
         text="Astronauts can grow a few centimetres taller in space, because their spines stretch without gravity pushing down.",
         q="What happens to astronauts' height in space?",
         options=["They get slightly taller", "They shrink a lot", "Nothing changes",
                  "They grow 1 metre"],
         true_s="Astronauts get a little taller in space as their spines stretch.",
         false_s="Astronauts shrink by about 30 centimetres in space."),
]

FACT_BY_ID = {f["id"]: f for f in FACTS}


class FactBook:
    """Tracks which facts the player has been shown (persisted in save data)."""

    def __init__(self, save):
        self.save = save

    @property
    def known(self):
        return [i for i in self.save.data["known_facts"] if i in FACT_BY_ID]

    def next_fact(self):
        """Pick a fact the player hasn't seen yet (or a random one if all seen)."""
        unseen = [f for f in FACTS if f["id"] not in self.save.data["known_facts"]]
        f = random.choice(unseen) if unseen else random.choice(FACTS)
        return f

    def learn(self, fact):
        if fact["id"] not in self.save.data["known_facts"]:
            self.save.data["known_facts"].append(fact["id"])
            self.save.save()

    def quiz(self, n):
        """n random known facts formatted as questions with shuffled options."""
        ids = random.sample(self.known, min(n, len(self.known)))
        out = []
        for i in ids:
            f = FACT_BY_ID[i]
            opts = list(f["options"])
            correct = opts[0]
            random.shuffle(opts)
            out.append(dict(fact=f, q=f["q"], options=opts, answer=opts.index(correct)))
        return out

    def statement(self):
        """(fact, statement, is_true) from a known fact."""
        f = FACT_BY_ID[random.choice(self.known)]
        truth = random.random() < 0.5
        return f, (f["true_s"] if truth else f["false_s"]), truth
