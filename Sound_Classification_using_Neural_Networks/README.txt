# Sound Classification Using Neural Networks

This project explores Deep Learning approaches for environmental sound classification, focusing primarily on Recurrent Neural Networks (RNNs) and the DeepFool adversarial attack. A Convolutional Neural Network (CNN) model is also included as required by the assignment. The workflow covers audio preprocessing, MFCC extraction, model training, evaluation, and robustness analysis.

----------------------------------------------------------

## Project Structure

Sound_Classification_using_Neural_Networks/
│── Project_CNN.ipynb
│── Project_RNN.ipynb
│── requirements.txt
│── data/  (not included in the repository)

----------------------------------------------------------

## Dataset

This project uses the **UrbanSound8K** dataset, which contains 8732 labeled sound excerpts from 10 urban sound classes.

Dataset download page:  
https://urbansounddataset.weebly.com/urbansound8k.html

----------------------------------------------------------

## Technologies Used

- Python 3.12.10  
- NumPy, Pandas  
- Librosa (audio processing)  
- Pytorch  
- Matplotlib 
- Jupyter Notebook  

----------------------------------------------------------

## How to Run the Project

1. **Install dependencies**
pip install -r requirements.txt


2. **Download the UrbanSound8K dataset**  


3. **Open the notebooks**

Project_CNN.ipynb
Project_RNN.ipynb

4. **Run all cells** to reproduce preprocessing, training, and evaluation.

----------------------------------------------------------

## Results

### **RNN Model**
- All models achieved similar moderate scores, with the LSTM trained on raw data performing best, contrary to our initial expectations. Several factors may explain this outcome. Most notably, the UrbanSound8K dataset is relatively small and may not provide enough examples for more complex architectures, such as the Attention‑based LSTM, to learn robust generalization. Another possible reason is the limited feature set: relying solely on MFCCs may restrict the model’s ability to capture complementary information. Incorporating additional features such as Mel spectrograms, Root Mean Square (RMS) energy, or Zero‑Crossing Rate (ZCR) could potentially highlight differences in model capacity more clearly and lead to improved performance.

### **Deepfool Model** 
The DeepFool evaluation shows that all RNN-based architectures implemented are highly vulnerable to adversarial perturbations, with a 100% attack success rate across all tested samples. Among the models, LSTM Raw exhibits the highest robustness (ρ_adv ≈ 0.0053), requiring the smallest relative perturbation to fool. In contrast, Attention LSTM is the most susceptible (ρ_adv ≈ 0.0282), indicating that despite its improved modeling capacity, the attention mechanism increases sensitivity to small adversarial changes. The normalized-feature models (LSTM Norm, BiLSTM, Deep BiLSTM) all fall within a similar vulnerability range (ρ_adv ≈ 0.017–0.018), suggesting that the use of MFCC-based normalized inputs does not inherently improve adversarial resilience. Overall, these results highlight that RNN architectures trained on sequential audio features are easily fooled by minimal perturbations, emphasizing the need for adversarial training or robustness-oriented regularization in future work. 

----------------------------------------------------------

## Key Insights

- CNNs are highly effective for MFCC‑based audio classification.  
- RNNs can model temporal structure but require more tuning.  
- Proper preprocessing (normalization, MFCC extraction) is crucial.  
- Data imbalance affects performance — augmentation could help.

----------------------------------------------------------

## Author

- **RNN models developed by:** Tiago Silva
- **CNN models developed by:** HUgo Souza
- **DeepFool adversarial analysis by:** Mariana Serralheiro
- **Project planning and methodological understanding:** Both authors  
(University of Porto — AI & Data Science)

----------------------------------------------------------

## License

This project is for academic and research purposes only.  
UrbanSound8K dataset is licensed separately by its creators.

