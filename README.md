
# Holodeck

**Holodeck** is a Python-based toolkit for procedural generation, editing, and management of 3D virtual environments, with seamless integration to Unity. It enables automated or interactive creation of complex scenes (such as houses, offices, or custom rooms) for research, simulation, or game development.

---

## Table of Contents

- [Features](#features)
- [Demo](#demo)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Scene Generation](#scene-generation)
  - [Unity Integration](#unity-integration)
  - [User Interface](#user-interface)
  - [Extending Holodeck](#extending-holodeck)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Data Format](#data-format)
- [Contributing](#contributing)
- [Testing & CI](#testing--ci)
- [License](#license)
- [Acknowledgements](#acknowledgements)
- [Contact](#contact)

---

## Features

- **Procedural 3D Scene Generation**: Create rooms, houses, offices, and more using Python scripts.
- **Object Placement & Layout**: Automatically place walls, doors, windows, furniture, lights, and small objects with support for layout constraints and optimization (MILP).
- **Unity Integration**: Export and send generated scenes to Unity for visualization and further editing.
- **Interactive UI**: Graphical interface for scene management and editing.
- **Extensible Architecture**: Easily add new object types, layouts, or connect to external 3D asset sources (e.g., Objaverse).
- **Scene Serialization**: Save and load scenes as JSON for reuse, sharing, or batch processing.
- **Prompt-based Generation**: Generate scenes from natural language prompts.
- **Open Source**: MIT licensed and ready for community contributions.

---

## Demo

<p align="center">
  <img src="https://user-images.githubusercontent.com/yourusername/holodeck-demo.gif" alt="Holodeck Demo" width="600"/>
</p>

*Above: Example of generating and visualizing a 3D house scene in Unity using Holodeck.*

---

## Installation

### Prerequisites

- Python 3.8+
- [Unity](https://unity.com/) (for visualization)
- pip

### Clone the Repository

```bash
git clone https://github.com/yourusername/holodeck.git
cd holodeck
```

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

### (Optional) Set Up a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

---

## Quick Start

1. **Generate a Scene**

   ```bash
   python ai2holodeck/main.py --prompt "a cozy living room with a sofa"
   ```

   This will generate a scene and save it as a JSON file in `data/scenes/`.

2. **Visualize in Unity**

   - Open Unity and run the Holodeck Unity integration.
   - Use `connect_to_unity.py` to send the generated scene to Unity:

     ```bash
     python connect_to_unity.py --scene data/scenes/a_cozy_living_room_with_a_sofa.json
     ```

3. **Edit with the UI**

   ```bash
   python holodeck_ui.py
   ```

---

## Usage

### Scene Generation

- Use the Python API or CLI to generate scenes from prompts or programmatically.
- Example (Python):

  ```python
  from ai2holodeck.generation.holodeck import generate_scene

  scene = generate_scene(prompt="a dentist office for children")
  scene.save("data/scenes/dentist_office.json")
  ```

- Scene files are saved as JSON in `data/scenes/`.

### Unity Integration

- Use `connect_to_unity.py` to send scene data to Unity.
- Unity must be running the Holodeck integration package to receive and render scenes.

### User Interface

- Run `holodeck_ui.py` for a graphical interface to view, edit, and manage scenes.

### Extending Holodeck

- Add new object types or layout logic in `ai2holodeck/generation/`.
- Integrate new 3D asset sources (e.g., Objaverse) via `objaverse_retriever.py`.
- Customize prompts and scene templates in `prompts.py`.

---

## Project Structure

```
holodeck/
│
├── ai2holodeck/                # Core library
│   ├── generation/             # Scene/object generation modules
│   ├── main.py                 # Main entry point for scene generation
│   └── ...
├── data/
│   └── scenes/                 # Generated scene JSON files
├── connect_to_unity.py         # Unity integration script
├── holodeck_ui.py              # Graphical user interface
├── app.py                      # (Optional) Web or API entry point
├── requirements.txt            # Python dependencies
├── setup.py                    # Package setup
├── .holodeck.env               # Environment/configuration file
├── .github/workflows/          # CI/CD workflows
└── README.md                   # This file
```

---

## Configuration

- Environment variables can be set in `.holodeck.env` for API keys, Unity connection details, etc.
- Scene generation parameters (e.g., object counts, layout constraints) can be customized in the generation modules.

---

## Data Format

- Scenes are stored as JSON files, describing all objects, their types, positions, and properties.
- Example snippet:

  ```json
  {
    "scene_name": "a_cozy_living_room_with_a_sofa",
    "objects": [
      {"type": "wall", "position": [0,0,0], "dimensions": [5,3,0.2]},
      {"type": "sofa", "position": [2,0,1], "color": "blue"},
      ...
    ]
  }
  ```

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

- Fork the repo and create your branch (`git checkout -b feature/your-feature`)
- Commit your changes (`git commit -am 'Add new feature'`)
- Push to the branch (`git push origin feature/your-feature`)
- Open a Pull Request

---

## Testing & CI

- Automated tests and linting are run via GitHub Actions (see `.github/workflows/`).
- To run tests locally:

  ```bash
  pytest
  ```

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Acknowledgements

- [Unity](https://unity.com/)
- [Objaverse](https://objaverse.allenai.org/)
- Open source contributors

---

## Contact

For questions, suggestions, or support, please open an issue or contact [your.email@example.com](mailto:your.email@example.com).

---

> Holodeck: Build, edit, and explore virtual worlds—programmatically.

---

You can further customize this README with badges, more detailed usage examples, or links to documentation as needed!
