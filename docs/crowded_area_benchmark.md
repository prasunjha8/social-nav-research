# Crowded-Area Benchmark

## Role In This Project

Keep `worlds/hospital_corridor.sdf` as the controlled environment for the primary PPO and VLM comparison. Use the Open-RMF Airport Terminal as a separate crowd-density stress test. Changing both the scene and the policy input at once would confound the result.

## Upstream Environment

Use the `2.0.4` release of [open-rmf/rmf_demos](https://github.com/open-rmf/rmf_demos/tree/2.0.4), which is pinned by the Open-RMF Humble release manifest. RMF Demos documents Ubuntu 22.04, ROS 2 Humble, and Gazebo Fortress, matching this project's stack. Its Airport Terminal launch supports the built-in Menge crowd simulation:

```bash
source /opt/ros/humble/setup.bash
ros2 launch rmf_demos_gz airport_terminal.launch.xml use_crowdsim:=1
```

This project does not install `rmf_demos_gz`; build/install the RMF Humble demo packages using the [upstream installation instructions](https://github.com/open-rmf/rmf). The map package generates the Ignition world and crowd resources during its build. It also downloads model assets into `~/.gazebo/models` unless configured not to, so a successful launch depends on those generated resources and downloaded assets being available.

Record the exact `rmf_demos` commit, build options, crowd configuration, and random seed with every experiment.

## Integration Boundary

The RMF launch starts its own airport world and demo systems. It does not currently spawn this project's Ackermann robot, connect this project's camera observation pipeline, or run `scripts/train_rl.py`. Treat it as an environment preview/stress-test target until those interfaces are explicitly integrated; do not count a standalone RMF run as a PPO baseline or VLM comparison.

A valid comparison in this scene will need the same robot, camera settings, policy checkpoints, crowd configuration, and episode seeds across methods. Log pedestrian density alongside proxemics violations, collisions, path legibility, and time to goal.

## License And Research Use

The `open-rmf/rmf_demos` repository is Apache-2.0 licensed. Research use, modification, and redistribution are permitted under that license; retain its license and copyright notices and record changes when redistributing covered files. This project has not copied RMF files or downloaded models into its source tree.

The RMF map build can download models from Gazebo Fuel. Those model assets may have licenses separate from the repository's Apache-2.0 license. Check each model's Fuel record and license before bundling, modifying, or redistributing it. Cite the RMF repository/commit and any reused model authors in publications and artifact documentation. This is a project compliance note, not legal advice.
