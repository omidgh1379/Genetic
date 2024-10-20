import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import joblib  # To load the PCA model
import io
from PIL import Image

# Function to load the PCA model
@st.cache_resource
def load_pca_model():
    # Load the pre-trained PCA model from the .pkl file
    pca_model = joblib.load('pca_model.pkl')
    return pca_model

# Load your dataset and PCA model
@st.cache_data
def load_data():
    # Load the known feature dataset (already processed)
    feature_df = pd.read_csv('feature_3d.csv')  # Processed known data with PCA and ethnicity
    return feature_df

# Helper function to process user-uploaded VCF data
def process_user_vcf(vcf_content):
    # Read the VCF file as a dataframe
    vcf_df = pd.read_csv(io.StringIO(vcf_content), sep='\t', skiprows=2,comment='#', header=None)
    
    # Drop unnecessary columns (#CHROM, POS, ID, REF, ALT, etc.)
    vcf_df = vcf_df.drop(columns=[0, 1, 2, 3, 4, 5, 6, 7, 8])  # Assuming the first 9 columns are metadata
    
    # Transpose the SNP data and rename columns
    transposed_vcf = vcf_df.transpose().reset_index(drop=True)
    transposed_vcf.columns = ["SNP_" + str(i) for i in range(1, len(transposed_vcf.columns) + 1)]
    
    # Replace the genotypes (e.g., 0|1, 1|1, etc.) with numerical values
    transposed_vcf.replace({'0|1': 1, '1|0': 1, '0|0': 0, '1|1': 2}, inplace=True)
    
    return transposed_vcf.values  # Return the SNP matrix

# Load the data and PCA model
feature_df = load_data()
pca = load_pca_model()  # Load the pre-trained PCA model from the .pkl file

# Set up page title and layout
st.title("Ethnicity Inference Using Genetic Variations (PCA)")

st.write("""
### Welcome to the Ethnicity Inference Tool!
Upload your SNP data file (VCF format) to infer your ethnicity. The system uses Principal Component Analysis (PCA) to predict ethnicity based on genetic information.
""")

# Section: Educational Explanation
st.header("How Does This System Work?")
st.write("""
This system uses **genotyping data** and **Principal Component Analysis (PCA)** to infer the ethnicity of unknown individuals based on their Single Nucleotide Polymorphisms (SNPs).
Here's a step-by-step breakdown:
""")

# Load images for explanation
pca_image = Image.open('pca_image.jpg')  # Replace with an actual image path
vcf_example_image = Image.open('VCF_image.png')  # Replace with an actual image path

# 1. Explain VCF files
st.subheader("Step 1: Understanding VCF Files")
st.write("""
VCF (Variant Call Format) files contain the genetic information of individuals. In this project, we are given genotyping data for 50 unknown samples and approximately 2,500 samples from the 1000 Genomes Project.

Each row in a VCF file represents a specific position on the genome, and the columns contain information about the alleles at that position for each individual.
""")
st.image(vcf_example_image, caption="VCF File Format Example")

# 2. Explain PCA
st.subheader("Step 2: Principal Component Analysis (PCA)")
st.write("""
PCA is a dimensionality reduction technique that helps to simplify complex datasets. For this ethnicity inference tool, we use PCA to reduce the dimensionality of the SNP data, making it easier to visualize and separate ethnic groups based on their genetic differences.
""")
st.image(pca_image, caption="PCA Plot Example")

st.write("""
- **PC1 and PC2**: These are the first two principal components that capture the most variance in the data.
- **Known Ethnicities**: Samples with known ethnicities from the 1000 Genomes Project.
- **Unknown Samples**: The samples for which we are trying to infer ethnicity.
""")

# Section 1: User file upload
uploaded_file = st.file_uploader("Upload your SNP data (VCF)", type="vcf")

if uploaded_file is not None:
    try:
        # Read the uploaded VCF file content
        vcf_content = uploaded_file.getvalue().decode("utf-8")
        
        # Process the VCF data
        user_snp_data = process_user_vcf(vcf_content)

        # Perform PCA transformation on user's data using the pre-trained PCA model
        user_pca = pca.transform(user_snp_data)[0]  # Get PCA components for user's data

        # Section 2: Interactive PCA plot with user's data point
        st.header("Interactive 3D PCA Plot with Your Data")

        # Plot the known data
        known_mask = feature_df["ethnicity"] != "Unknown"
        unknown_mask = feature_df["ethnicity"] == "Unknown"

        # Known samples plot
        known_trace = go.Scatter3d(
            x=feature_df.loc[known_mask, "PC1"],
            y=feature_df.loc[known_mask, "PC2"],
            z=feature_df.loc[known_mask, "PC3"],
            mode='markers',
            marker=dict(size=5, color=pd.Categorical(feature_df.loc[known_mask, "ethnicity"]).codes, colorscale='Viridis', opacity=0.8),
            text=feature_df.loc[known_mask, "ethnicity"],
            name='Known Ethnicities'
        )

        # Unknown samples plot
        unknown_trace = go.Scatter3d(
            x=feature_df.loc[unknown_mask, "PC1"],
            y=feature_df.loc[unknown_mask, "PC2"],
            z=feature_df.loc[unknown_mask, "PC3"],
            mode='markers',
            marker=dict(size=10, color='red', symbol='x', opacity=0.9),
            text="Unknown",
            name='Unknown Ethnicity'
        )

        # Plot the user's data point
        user_trace = go.Scatter3d(
            x=[user_pca[0]],
            y=[user_pca[1]],
            z=[user_pca[2]],
            mode='markers',
            marker=dict(size=12, color='blue', symbol='diamond'),
            text="Your SNP data",
            name='Your SNP data'
        )

        # Set up layout for the 3D plot
        layout = go.Layout(
            scene=dict(xaxis=dict(title="PC1"), yaxis=dict(title="PC2"), zaxis=dict(title="PC3")),
            title="3D PCA Plot: Genetic Data and Ethnicity",
            showlegend=True
        )

        # Create figure with known, unknown, and user's data points
        fig = go.Figure(data=[known_trace, unknown_trace, user_trace], layout=layout)

        # Display the plot
        st.plotly_chart(fig)

        # Conclusion about ethnicity based on proximity in PCA space
        st.write("Your SNP data has been plotted in the PCA space. Based on the proximity to known ethnic groups, your ethnicity can be inferred.")

    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")

# Section 3: More technical details
st.header("Technical Details")

st.write("""
### Data Processing and PCA
1. **VCF Parsing**: The SNPs from the VCF file are read and converted into a numeric matrix where:
    - 0|0 represents homozygous reference (0)
    - 0|1 or 1|0 represents heterozygous (1)
    - 1|1 represents homozygous alternative (2)

2. **PCA Application**: We apply Principal Component Analysis (PCA) to reduce the dimensionality of the SNP data, creating a low-dimensional representation of each individual's genetic makeup.

3. **Ethnicity Inference**: Once the PCA is computed, unknown samples are plotted on the PCA graph. We infer their ethnicity based on their proximity to known population clusters (from the 1000 Genomes Project).

### Conclusion:
PCA allows us to project genetic data into a 2D or 3D space, enabling clear separation of ethnicities based on genetic similarity. The "Unknown" samples' positions in this space help us predict their likely ethnicity.
""")
