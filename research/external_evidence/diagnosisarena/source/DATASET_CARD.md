---
dataset_info:
  features:
  - name: id
    dtype: int64
  - name: Case Information
    dtype: string
  - name: Physical Examination
    dtype: string
  - name: Diagnostic Tests
    dtype: string
  - name: Final Diagnosis
    dtype: string
  - name: Options
    struct:
    - name: A
      dtype: string
    - name: B
      dtype: string
    - name: C
      dtype: string
    - name: D
      dtype: string
  - name: Right Option
    dtype: string
  splits:
  - name: test
    num_bytes: 1562755
    num_examples: 915
  download_size: 870485
  dataset_size: 1562755
configs:
- config_name: default
  data_files:
  - split: test
    path: data/test-*
---
# DiagnosisArena: Benchmarking Diagnostic Reasoning for Large Language Models

**DiagnosisArena** is a comprehensive and challenging medical benchmark designed to assess the diagnostic reasoning abilities of LLMs in clinical settings. 
This benchmark consists of 915 pairs of segmented patient cases and corresponding diagnoses, spanning 28 medical specialties, deriving from clinical case reports published in 10 high-impact medical journals. 
The experimental results indicate that even the SOTA reasoning models perform relatively poorly on **DiagnosisArena**.

## An Example to load the data

```python
from datasets import load_dataset
dataset=load_dataset("SII-SPIRAL-MED/DiagnosisArena", split="test")
print(dataset[0])
```

More details on loading and using the data are at our [GitHub Page](https://github.com/SPIRAL-MED/DiagnosisArena).

## Citation

If you do find our code helpful or use our benchmark dataset, please cite our paper.
```
@article{zhu2025diagnosisarena,
  title={DiagnosisArena: Benchmarking Diagnostic Reasoning for Large Language Models},
  author={Zhu, Yakun and Huang, Zhongzhen and Mu, Linjie and Huang, Yutong and Nie, Wei and Zhang, Shaoting and Liu, Pengfei and Zhang, Xiaofan},
  journal={arXiv preprint arXiv:2505.14107},
  year={2025}
}
```

## Disclaimer and Terms of Use

This dataset is adapted from publicly available literature, including publications from Cell, JAMA, and similar sources. All case data has been de-identified.
**This dataset is provided for research and model evaluation purposes only. It must not be used for clinical decision-making or medical diagnosis.**