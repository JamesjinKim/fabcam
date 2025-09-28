# Claude Rules for Shinho Project

## Project Overview
This project contains multiple sub-projects:
- FabCam: CCTV system with Raspberry Pi and Picamera2 integration
- Aircon: Air conditioning control system

## Development Guidelines

### Code Style
- Follow Python PEP 8 conventions
- Use meaningful variable and function names
- Keep functions focused and small
- Add type hints where appropriate
- 답글은 항상 한글로 해야 함.

### Testing
- Run tests before committing changes
- Test commands:
  ```bash
  # For Python projects
  python -m pytest
  
  # For linting
  ruff check .
  ruff format .
  ```

### Git Workflow
- Make atomic commits with clear messages
- Always check git status before committing
- Use descriptive commit messages

### Project-Specific Rules

#### FabCam
- Use Picamera2 for camera operations on Raspberry Pi
- Store recordings in `FabCam/static/videos/`
- Store snapshots in `FabCam/static/images/`
- Backend runs on FastAPI
- Frontend uses vanilla HTML/CSS/JavaScript

#### Aircon
- Follow the existing project structure
- Maintain compatibility with air conditioning hardware interfaces

### Security
- Never commit sensitive credentials
- Use environment variables for configuration
- Validate all user inputs

### Performance
- Optimize for Raspberry Pi hardware limitations
- Use appropriate video compression settings
- Monitor memory usage for long-running processes