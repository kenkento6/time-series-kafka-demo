import torch
import torch.nn as nn

class MyCNN(nn.Module):
	
	def __init__(self):
		# self.MAGIC_NUMBER = 16*41
		super(MyCNN, self).__init__()
		self.conv1 = nn.Conv1d(in_channels=7, out_channels=4, kernel_size=5)
		self.conv2 = nn.Conv1d(in_channels=4, out_channels=1, kernel_size=5)
		self.pool = nn.MaxPool1d(kernel_size=2, stride=2)
		# self.out = nn.Linear(in_features=567, out_features=1)

		self.dropout = nn.Dropout(0.5)
		self.lstm = nn.LSTM(input_size = 27, hidden_size=16, num_layers=2)
		self.out = nn.Linear(in_features=16, out_features=2)

	def forward(self, x):
		x = torch.tanh(self.conv1(x))
		x = self.pool(x)
		x = torch.tanh(self.conv2(x))
		x = self.pool(x)
		x = self.dropout(x)
		x = x.view(-1, 27)
		x,_ = self.lstm(x)
		x = self.out(x)
		# x = self.out(x)
		return x
