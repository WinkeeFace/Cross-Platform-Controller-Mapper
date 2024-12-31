# [WIP] Cross-Platform Controller Mapper

A **cross-platform controller mapping tool** designed to provide functionality similar to REWASD, but with **support for MacOS**, **Windows**, and (future) **Linux**. This project is currently a work in progress, and while it is **actively tested on MacOS**, I aim to expand support to other platforms based on user feedback and requests.

## 🌟 Features
- **Platform Support**: MacOS (actively tested), with planned support for Windows and Linux.
- **Customizable Profiles**: Create and switch between multiple mapping profiles tailored to different applications.
- **Button and Axis Mapping**: Map controller buttons and axes to keyboard, mouse, or custom actions.
- **Combos and Sequences**: Define complex button combinations and sequences for streamlined workflows or advanced inputs.
- **Human-Friendly Mappings**: Export profiles in an easy-to-read format for review and sharing.
- **Accessibility First**: Focused on improving accessibility for workflows, gaming, and everyday tasks.

## 🚧 Current Status
This project is **under development** and not yet fully functional. However, core features are in place, and I am actively working on modularity, usability improvements, and extended functionality. 

If you need support for a specific platform (Windows or Linux), or require certain features, please [submit an issue](https://github.com/WinkeeFace/Cross-Platform-Controller-Mapper/issues) or contact me directly. I’ll prioritize requests based on demand.

## 🚀 Planned Features
- **Verbose Configuration Options**: Allow users to input arrays for multi-command actions.
- **Combo Management**: Add hash-map-based design patterns for handling input combinations.
- **Improved Axis and Trigger Handling**: Refine normalization and deadzone support for joysticks and triggers.
- **Executable Version**: Package the tool as a standalone executable for easy usage without requiring a development environment.

For a complete list of tasks and enhancements, check out the [GitHub Issues](https://github.com/WinkeeFace/Cross-Platform-Controller-Mapper/issues).

## 📂 Installation
### Prerequisites
- Python 3.7+
- `pip` package manager

### Installation Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/WinkeeFace/Cross-Platform-Controller-Mapper.git
   cd Cross-Platform-Controller-Mapper
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the tool:
   ```bash
   python main.py
   ```

## 🛠 Usage
### Running the Controller Mapper
To start mapping your controller:
```bash
python main.py run
```

### Example Commands
- List current mappings:
  ```bash
  python main.py list
  ```
- Add a new button mapping:
  ```bash
  python main.py add -b 1 -a "Key.space"
  ```
- Interactively map inputs:
  ```bash
  python main.py map
  ```

### Configuration File
The tool uses a JSON-based configuration file (`config.json`) to store mappings and profiles. Here’s a sample:
```json
{
    "profiles": [
        {
            "name": "default",
            "mappings": {
                "buttons": {"1": "Key.space"},
                "axes": {"0": "MouseMoveHorizontal"}
            }
        }
    ]
}
```

## 💡 Why This Project?
REWASD doesn’t support MacOS, which I rely on for work. This project began as a way to bridge that gap and improve my personal workflow. However, I’m passionate about accessibility and want to share this tool with others who might benefit.

If you’re looking for cross-platform controller mapping with MacOS support—or have specific features you’d like to see—please [let me know](https://github.com/WinkeeFace/Cross-Platform-Controller-Mapper/issues).

## 🤝 Contributing
Contributions are welcome! If you’d like to contribute:
1. Fork the repository.
2. Create a new branch:
   ```bash
   git checkout -b feature-name
   ```
3. Commit your changes and push them to your branch.
4. Open a pull request.

### Found an Issue or Have a Request?
Check the [Issues](https://github.com/WinkeeFace/Cross-Platform-Controller-Mapper/issues) tab or submit your own! I’d love to hear your feedback and ideas.

## 🛡 License
This project is licensed under the [Apache 2.0 License](LICENSE).

---

## 📧 Contact
If you have any questions, feedback, or requests, feel free to reach out via GitHub Issues or pull requests. Your input will help shape the future of this project!

---
